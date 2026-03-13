from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass(frozen=True)
class MarkerInjectResult:
    updated_source: str
    changed_functions: List[str]
    skipped_functions: List[str]


def inject_testai_markers(
    file_path: str | Path,
    functions_to_mark: List[str],
    marker_line: str,
) -> MarkerInjectResult:
    """
    Inserts '# @testai spec=...' as the first non-docstring line inside each function body.
    If already present (matching prefix '# @testai'), it replaces it with marker_line.
    """
    path = Path(file_path)
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()

    tree = ast.parse(source, filename=str(path))

    edits: List[Tuple[int, int, List[str]]] = []
    changed: List[str] = []
    skipped: List[str] = []

    wanted = set(functions_to_mark)
    marker_prefix = "# @testai"

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in wanted:
            continue

        body_indent = " " * (getattr(node, "col_offset", 0) + 4)
        marker = body_indent + marker_line

        # Determine insertion point: after docstring expr if present, else first body line
        insert_index_0based = None

        has_doc_stmt = (
            len(node.body) > 0
            and isinstance(node.body[0], ast.Expr)
            and isinstance(getattr(node.body[0], "value", None), ast.Constant)
            and isinstance(node.body[0].value.value, str)
        )

        if has_doc_stmt:
            doc_stmt = node.body[0]
            # insert after docstring statement line range
            insert_index_0based = doc_stmt.end_lineno  # 1-based, insert after => index = end_lineno
        else:
            insert_index_0based = node.lineno  # insert right after def line

        # Check a small window of first few body lines for existing marker
        # (starting at insert_index_0based and a couple lines after)
        start_scan = insert_index_0based
        end_scan = min(insert_index_0based + 3, len(lines))

        existing_line_idx = None
        for i in range(start_scan, end_scan):
            if lines[i].lstrip().startswith(marker_prefix):
                existing_line_idx = i
                break

        if existing_line_idx is not None:
            # Replace existing marker line
            edits.append((existing_line_idx, existing_line_idx, [marker]))
            changed.append(node.name)
        else:
            # Insert marker line at insert_index_0based
            edits.append((insert_index_0based, insert_index_0based - 1, [marker]))
            changed.append(node.name)

    edits.sort(key=lambda e: (e[0], e[1]), reverse=True)

    new_lines = lines[:]
    for start, end, repl in edits:
        if start <= end:
            new_lines[start : end + 1] = repl
        else:
            new_lines[start:start] = repl

    updated = "\n".join(new_lines) + ("\n" if source.endswith("\n") else "")
    return MarkerInjectResult(updated, changed, skipped)
