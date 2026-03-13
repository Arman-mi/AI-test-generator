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
from test_ai.core.spec_store import load_sidecar, save_sidecar, spec_path_for_target, SidecarSpec
from test_ai.languages.python.marker_inject import inject_testai_markers




def _cmd_gen(path_str: str) -> int:
    target_path = Path(path_str)
    if not target_path.exists():
        print(f"Error: file not found: {target_path}", file=sys.stderr)
        return 2
    if target_path.suffix != ".py":
        print(f"Error: only .py files supported for now: {target_path}", file=sys.stderr)
        return 2

    sidecar_path = spec_path_for_target(target_path)
    sidecar = load_sidecar(sidecar_path)
    if sidecar is None:
        print(f"Error: spec file not found: {sidecar_path}", file=sys.stderr)
        print("Run: test-ai spec <file.py> first")
        return 2

    # Filter specs to functions that actually exist in the target file
    funcs = discover_functions(target_path)
    existing_names = {f.name for f in funcs}

    specs = {}
    missing = []
    for name, spec_obj in sidecar.functions.items():
        if name in existing_names:
            specs[name] = spec_obj
        else:
            missing.append(name)

    if missing:
        print("Warning: spec file contains functions not found in source:", ", ".join(missing))

    test_text = render_pytest_for_module(str(target_path), specs)

    out_dir = Path("tests")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"test_{target_path.stem}.py"
    out_path.write_text(test_text, encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0

def _cmd_spec(path_str: str, dry_run: bool, force: bool) -> int:
    target_path = Path(path_str)
    if not target_path.exists():
        print(f"Error: file not found: {target_path}", file=sys.stderr)
        return 2
    if target_path.suffix != ".py":
        print(f"Error: only .py files supported for now: {target_path}", file=sys.stderr)
        return 2

    sidecar_path = spec_path_for_target(target_path)
    existing = load_sidecar(sidecar_path)

    functions_map = dict(existing.functions) if existing else {}
    client = LLMClient()

    funcs = discover_functions(target_path)
    generated = []

    for f in funcs:
        if (not force) and (f.name in functions_map):
            continue

        signature = f"{f.name}({', '.join(f.args)})"
        ctx = FunctionContext(
            file_path=str(target_path),
            function_name=f.name,
            signature=signature,
            docstring=f.docstring,
            source_snippet=None,
        )

        spec_obj = client.generate_test_spec(ctx)
        functions_map[f.name] = spec_obj
        generated.append(f.name)
        print(f"Generated spec for: {f.name}")

    if not generated:
        print("No new specs generated (already up to date).")
        return 0

    new_sidecar = SidecarSpec(version=1, target=str(target_path), functions=functions_map)

    marker_line = f"# @testai spec={sidecar_path.as_posix()}"
    marker_result = inject_testai_markers(target_path, generated, marker_line)

    if dry_run:
        print(f"\n--- DRY RUN ---")
        print(f"Would write: {sidecar_path}")
        print(f"Would update markers in: {target_path} for: {', '.join(marker_result.changed_functions)}")
        return 0

    save_sidecar(sidecar_path, new_sidecar)
    target_path.write_text(marker_result.updated_source, encoding="utf-8")

    print(f"Wrote: {sidecar_path}")
    print(f"Updated markers in: {target_path}")
    return 0




def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="test-ai", description="LLM-assisted TDD test generator (Python v1)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("gen", help="Generate pytest tests from @testai_json blocks")
    p_gen.add_argument("path", help="Path to a Python file, e.g. example.py")
    p_spec = sub.add_parser("spec", help="Generate sidecar spec JSON using the LLM")
    p_spec.add_argument("path", help="Path to a Python file, e.g. hello.py")
    p_spec.add_argument("--dry-run", action="store_true", help="Do not write changes to disk")
    p_spec.add_argument("--force", action="store_true", help="Regenerate specs even if already present")



    args = parser.parse_args(argv)

    if args.cmd == "gen":
        return _cmd_gen(args.path)
    if args.cmd == "spec":
        return _cmd_spec(args.path, args.dry_run,args.force)


    # Should be unreachable due to required=True
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
