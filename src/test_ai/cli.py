from __future__ import annotations

import argparse
from pathlib import Path
import sys

from test_ai.languages.python.discover import discover_functions
from test_ai.languages.python.spec_extract import extract_testai_json
from test_ai.languages.python.render_pytest import render_pytest_for_module
from test_ai.llm.client import LLMClient
from test_ai.llm.prompts import FunctionContext
from test_ai.languages.python.spec_inject import inject_specs_into_file



def _cmd_gen(path_str: str) -> int:
    target_path = Path(path_str)
    if not target_path.exists():
        print(f"Error: file not found: {target_path}", file=sys.stderr)
        return 2
    if target_path.suffix != ".py":
        print(f"Error: only .py files supported for now: {target_path}", file=sys.stderr)
        return 2

    funcs = discover_functions(target_path)

    discovered_payload = []
    skipped = []
    for f in funcs:
        spec = extract_testai_json(f.docstring)
        if spec is None:
            skipped.append(f.name)
            continue
        discovered_payload.append(
            {
                "name": f.name,
                "args": f.args,
                "spec": spec,
            }
        )

    if skipped:
        for name in skipped:
            print(f"Warning: {name} has no @testai_json block; skipping.")

    # Render tests (renderer should import by file path internally)
    test_text = render_pytest_for_module(str(target_path), discovered_payload)

    out_dir = Path("tests")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"test_{target_path.stem}.py"
    out_path.write_text(test_text, encoding="utf-8")

    print(f"Wrote: {out_path}")

    if not discovered_payload:
        print("Note: no specs found; generated file may contain only a comment.")
        return 1

    return 0
def _cmd_spec(path_str: str, dry_run: bool) -> int:
    target_path = Path(path_str)
    if not target_path.exists():
        print(f"Error: file not found: {target_path}", file=sys.stderr)
        return 2
    if target_path.suffix != ".py":
        print(f"Error: only .py files supported for now: {target_path}", file=sys.stderr)
        return 2

    funcs = discover_functions(target_path)

    client = LLMClient()

    specs_by_fn = {}
    for f in funcs:
        # Skip if already has a spec
        existing = extract_testai_json(f.docstring)
        if existing is not None:
            continue

        signature = f"{f.name}({', '.join(f.args)})"
        ctx = FunctionContext(
            file_path=str(target_path),
            function_name=f.name,
            signature=signature,
            docstring=f.docstring,
            source_snippet=None,
        )

        spec = client.generate_test_spec(ctx)  # returns {"cases":[...], "raises":[...]}
        specs_by_fn[f.name] = spec
        print(f"Generated spec for: {f.name}")

    if not specs_by_fn:
        print("No missing @testai_json blocks found.")
        return 0

    result = inject_specs_into_file(target_path, specs_by_fn)

    print(f"Will update: {', '.join(result.changed_functions)}")
    if result.skipped_functions:
        print(f"Skipped (already had marker): {', '.join(result.skipped_functions)}")

    if dry_run:
        print("\n--- DRY RUN: no file written ---")
        return 0

    target_path.write_text(result.updated_source, encoding="utf-8")
    print(f"Wrote updated specs into: {target_path}")
    return 0



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="test-ai", description="LLM-assisted TDD test generator (Python v1)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("gen", help="Generate pytest tests from @testai_json blocks")
    p_gen.add_argument("path", help="Path to a Python file, e.g. example.py")
    p_spec = sub.add_parser("spec", help="Generate @testai_json blocks using the LLM")
    p_spec.add_argument("path", help="Path to a Python file, e.g. example.py")
    p_spec.add_argument("--dry-run", action="store_true", help="Do not write changes to disk")


    args = parser.parse_args(argv)

    if args.cmd == "gen":
        return _cmd_gen(args.path)
    if args.cmd == "spec":
        return _cmd_spec(args.path, args.dry_run)


    # Should be unreachable due to required=True
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
