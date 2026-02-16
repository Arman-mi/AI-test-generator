from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from openai import OpenAI

from test_ai.llm.prompts import FunctionContext, build_messages
from dotenv import load_dotenv
load_dotenv()


def _json_value_schema() -> Dict[str, Any]:
    """
    JSON Schema fragment representing any JSON value.
    """
    return {
        "type": ["null", "boolean", "number", "string", "array", "object"],
        "additionalProperties": True,
        "items": {},  # allow any array items
    }


def _validate_spec(data: dict) -> None:
    if not isinstance(data, dict):
        raise RuntimeError("Spec must be a JSON object.")

    if "cases" not in data or "raises" not in data:
        raise RuntimeError("Spec must have top-level keys: 'cases' and 'raises'.")

    if not isinstance(data["cases"], list):
        raise RuntimeError("'cases' must be a list.")
    if not isinstance(data["raises"], list):
        raise RuntimeError("'raises' must be a list.")

    for i, case in enumerate(data["cases"]):
        if not isinstance(case, dict):
            raise RuntimeError(f"cases[{i}] must be an object.")
        if "in" not in case or "out" not in case:
            raise RuntimeError(f"cases[{i}] must have keys 'in' and 'out'.")
        if not isinstance(case["in"], dict):
            raise RuntimeError(f"cases[{i}]['in'] must be an object.")

    for i, r in enumerate(data["raises"]):
        if not isinstance(r, dict):
            raise RuntimeError(f"raises[{i}] must be an object.")
        if "in" not in r or "type" not in r:
            raise RuntimeError(f"raises[{i}] must have keys 'in' and 'type'.")
        if not isinstance(r["in"], dict):
            raise RuntimeError(f"raises[{i}]['in'] must be an object.")
        if not isinstance(r["type"], str):
            raise RuntimeError(f"raises[{i}]['type'] must be a string.")
        if "match" in r and not isinstance(r["match"], str):
            raise RuntimeError(f"raises[{i}]['match'] must be a string if present.")



def _spec_schema() -> Dict[str, Any]:
    """
    JSON Schema for:
      {
        "cases": [{"in": {...}, "out": <any-json>}...],
        "raises": [{"in": {...}, "type": "ValueError", "match": "..."}...]
      }
    """
    any_json = _json_value_schema()

    return {
        "name": "testai_spec",
        "schema": {
            "type": "object",
            "properties": {
                "cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "in": {
                                "type": "object",
                                "additionalProperties": True,
                            },
                            "out": any_json,
                        },
                        "required": ["in", "out"],
                        "additionalProperties": False,
                    },
                },
                "raises": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "in": {
                                "type": "object",
                                "additionalProperties": True,
                            },
                            "type": {"type": "string"},
                            "match": {"type": "string"},
                        },
                        "required": ["in", "type"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["cases", "raises"],
            "additionalProperties": False,
        },
        "strict": True,
    }


@dataclass
class LLMConfig:
    model: str = "gpt-4o-mini"  # Structured Outputs supported on gpt-4o-mini & later snapshots :contentReference[oaicite:1]{index=1}
    temperature: float = 0.2
    max_tokens: int = 800


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Set it in your environment before running `spec`."
            )
        self.client = OpenAI(api_key=api_key)
        self.config = config or LLMConfig(
            model=os.getenv("TEST_AI_MODEL", LLMConfig.model),
            temperature=float(os.getenv("TEST_AI_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("TEST_AI_MAX_TOKENS", "800")),
        )

    def generate_test_spec(self, ctx: FunctionContext) -> Dict[str, Any]:
        """
        Calls the LLM and returns a Python dict shaped like:
          {"cases": [...], "raises": [...]}

        Uses Structured Outputs (json_schema) to enforce schema compliance. :contentReference[oaicite:2]{index=2}
        """
        messages = build_messages(ctx)

        resp = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            response_format={
                "type": "json_object"},
        )

        # The SDK returns the assistant message content as a JSON string.
        # Structured Outputs makes it schema-compliant, but we still parse it into a dict.
        content = resp.choices[0].message.content
        if not content:
            raise RuntimeError("LLM returned empty content.")

        try:
            data = json.loads(content)

        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM returned non-JSON content unexpectedly: {e}\nCONTENT:\n{content}") from e

        # Minimal sanity checks (schema should already enforce these)
        if not isinstance(data, dict) or "cases" not in data or "raises" not in data:
            raise RuntimeError(f"LLM returned unexpected shape: {data}")
        _validate_spec(data)
        return data
