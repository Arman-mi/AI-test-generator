from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


MARKER = "@testai_json:"


@dataclass(frozen=True)
class InjectResult:
    updated_source: str
    changed_functions: List[str]
    skipped_functions: List[str]


def _indent_lines(text: str, indent: str) -> str:
    return "\n".join((indent + line if line else indent.rstrip()) for line in text.splitlines())


def _format_testai_block(spec: Dict[str, Any]) -> str:
    # Pretty JSON for readability in docstrings.
    return json.dumps(spec, indent=2, ensure_ascii=False)


def _has_marker(docstring: Optional[str]) -> bool:
    return bool(docstring and MARKER in docstring)


def _build_docstring(existing_doc: Optional[str], spec: Dict[str, Any]) -> str:
    # Keep the existing docstring text (cleaned by AST) if present.
    doc_top = (existing_doc or "").strip()
    if doc_top:
        body = doc_top + "\n\n" + MARKER + "\n" + _format_testai_block(spec)
    else:
        body = MARKER + "\n" + _format_testai_block(spec)

    # Normalize to triple-double quotes
    return f'"""\n{body}\n"""'


def inject_specs_into_file(
    file_path: str | Path,
    specs_by_function: Dict[str, Dict[str, Any]],
) -> InjectResult:
    """
    Insert/replace docstrings for top-level functions in file_path, adding @testai_json blocks.

    - If function already has @testai_json in its docstring -> skipped
    - Else if has docstring stmt -> replace that whole stmt with our normalized docstring
    - Else -> insert a docstring stmt as the first line in the function body
    """
    path = Path(file_path)
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()

    tree = ast.parse(source, filename=str(path))

    # Collect edits as (start_line_idx, end_line_idx, replacement_lines)
    edits: List[Tuple[int, int, List[str]]] = []

    changed: List[str] = []
    skipped: List[str] = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        fn_name = node.name
        if fn_name not in specs_by_function:
            continue

        existing_doc = ast.get_docstring(node)  # cleaned text or None
        if _has_marker(existing_doc):
            skipped.append(fn_name)
            continue

        spec = specs_by_function[fn_name]
        new_doc_stmt = _build_docstring(existing_doc, spec)

        # Determine indentation
        fn_indent = " " * getattr(node, "col_offset", 0)
        body_indent = " " * (getattr(node, "col_offset", 0) + 4)

        # Replace docstring statement if present
        has_doc_stmt = (
            len(node.body) > 0
            and isinstance(node.body[0], ast.Expr)
            and isinstance(getattr(node.body[0], "value", None), ast.Constant)
            and isinstance(node.body[0].value.value, str)
        )

        if has_doc_stmt:
            doc_stmt = node.body[0]
            start = doc_stmt.lineno - 1
            end = doc_stmt.end_lineno - 1  # inclusive
            replacement = _indent_lines(new_doc_stmt, body_indent).splitlines()
            edits.append((start, end, replacement))
        else:
            # Insert after the def line
            insert_at = node.lineno  # lineno is 1-based; insert after that line => index == lineno
            replacement = _indent_lines(new_doc_stmt, body_indent).splitlines()
            edits.append((insert_at, insert_at - 1, replacement))  # empty range = insertion

        changed.append(fn_name)

    # Apply edits bottom-up so line indices remain valid
    edits.sort(key=lambda e: (e[0], e[1]), reverse=True)

    new_lines = lines[:]
    for start, end, repl in edits:
        if start <= end:
            new_lines[start : end + 1] = repl
        else:
            # insertion at index `start`
            new_lines[start:start] = repl

    updated_source = "\n".join(new_lines) + ("\n" if source.endswith("\n") else "")
    return InjectResult(updated_source, changed, skipped)
