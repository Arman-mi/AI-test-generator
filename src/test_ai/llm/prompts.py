from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


SYSTEM_PROMPT = """\
You generate test specifications for TDD.

Return ONLY JSON that matches the provided JSON Schema.
Do NOT include markdown fences, comments, or extra keys.

Guidelines:
- Prefer small, deterministic inputs.
- Include typical cases + edge cases + at least one invalid input (if sensible) under `raises`.
- Keep inputs JSON-serializable (null/boolean/number/string/array/object).
- Use parameter names exactly as in the function signature for the `in` object.
- If the function is underspecified, make reasonable assumptions and cover them with tests.
"""


@dataclass(frozen=True)
class FunctionContext:
    file_path: str
    function_name: str
    signature: str                 # e.g. "is_even(x)"
    docstring: Optional[str]       # raw docstring (may be None)
    # Optional extras for later:
    source_snippet: Optional[str] = None


def build_messages(ctx: FunctionContext) -> list[dict]:
    """
    Returns OpenAI chat messages: [{"role": "...", "content": "..."}]
    """
    doc = ctx.docstring.strip() if ctx.docstring else "(no docstring provided)"
    snippet = ctx.source_snippet.strip() if ctx.source_snippet else "(not provided)"

    user_prompt = f"""\
Target file: {ctx.file_path}

Function:
- name: {ctx.function_name}
- signature: {ctx.signature}

Existing docstring:
{doc}

Source snippet (optional context):
{snippet}

Task:
Generate a JSON object with two keys: "cases" and "raises".

- "cases": a list of objects, each object has:
  - "in": object mapping parameter names -> input values
  - "out": expected return value

- "raises": a list of objects, each object has:
  - "in": object mapping parameter names -> input values
  - "type": exception class name as a string (e.g., "ValueError", "TypeError")
  - optionally "match": a substring or regex for the exception message

Notes:
- If it returns True/False, include both True and False cases.
- If None is a valid output, include it explicitly.
- If the function mutates inputs or returns complex objects, approximate with JSON-friendly values.
"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
