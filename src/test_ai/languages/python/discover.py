# src/test_ai/languages/python/discover.py

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class DiscoveredFunction:
    name: str
    args: List[str]                 # positional arg names (incl. self if present)
    kwonly_args: List[str]          # keyword-only arg names
    vararg: Optional[str]           # *args name
    kwarg: Optional[str]            # **kwargs name
    docstring: Optional[str]
    lineno: int                     # 1-based
    end_lineno: int                 # 1-based (best effort)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

#takes in a path object or a string path
def discover_functions(file_path: str | Path) -> List[DiscoveredFunction]:
    """
    Discover *top-level* function definitions in a Python file.

    Notes:
    - Only finds `def foo(...):` at module level (not class methods yet).
    - Uses Python AST, so it's robust (no regex).
    """
    #turns either string path or path object into a path object
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    source = _read_text(path)
    tree = ast.parse(source, filename=str(path))

    results: List[DiscoveredFunction] = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            results.append(_extract_function(node))
        elif isinstance(node, ast.AsyncFunctionDef):
            # Optional: treat async defs like normal defs for discovery
            results.append(_extract_function(node))

    return results


def _extract_function(node: ast.AST) -> DiscoveredFunction:
    # node is ast.FunctionDef or ast.AsyncFunctionDef
    assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))

    args = [a.arg for a in node.args.args]  # positional (includes self if present)
    kwonly_args = [a.arg for a in node.args.kwonlyargs]
    vararg = node.args.vararg.arg if node.args.vararg else None
    kwarg = node.args.kwarg.arg if node.args.kwarg else None

    doc = ast.get_docstring(node)  # returns cleaned docstring or None

    lineno = getattr(node, "lineno", 1)
    end_lineno = getattr(node, "end_lineno", lineno)

    return DiscoveredFunction(
        name=node.name,
        args=args,
        kwonly_args=kwonly_args,
        vararg=vararg,
        kwarg=kwarg,
        docstring=doc,
        lineno=lineno,
        end_lineno=end_lineno,
    )
