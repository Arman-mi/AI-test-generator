from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _safe_ident(s: str) -> str:
    """
    Make a safe-ish python identifier chunk for test names.
    """
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "x"


def _py_literal(value: Any) -> str:
    """
    Convert a parsed JSON value (None/bool/int/float/str/list/dict) into Python code.
    For JSON, repr() is enough.
    """
    return repr(value)


def render_pytest_for_module(
    module_path: str,
    discovered: List[Dict[str, Any]],
) -> str:
    """
    Render a pytest file for one module.

    discovered items look like:
      {"name": "preorder", "args": ["root"], "spec": {...} or None}
    """
    lines: List[str] = []
    lines.append("import pytest")
                 #commented out for now different iteration                                        # lines.append(f"import {module_path}")
                 # trying something else                                       # lines.append("")
                                                        # lines.append("import pytest")
    lines.append("import importlib.util")
    lines.append("from pathlib import Path")
    lines.append("")
    lines.append(f"MODULE_PATH = Path({repr(module_path)}).resolve()")
    lines.append("spec = importlib.util.spec_from_file_location('target_module', MODULE_PATH)")
    lines.append("target_module = importlib.util.module_from_spec(spec)")
    lines.append("assert spec and spec.loader")
    lines.append("spec.loader.exec_module(target_module)")
    lines.append("")


    for fn in discovered:
        fn_name: str = fn["name"]
        spec: Optional[Dict[str, Any]] = fn.get("spec")

        if not spec:
            continue

        cases = spec.get("cases", []) or []
        raises_cases = spec.get("raises", []) or []

        # ---- normal cases ----
        if cases:
            param_rows: List[str] = []
            for case in cases:
                case_in = case.get("in", {})
                expected = case.get("out", None)
                param_rows.append(f"    ({_py_literal(case_in)}, {_py_literal(expected)}),")

            test_name = f"test_{_safe_ident(fn_name)}_cases"
            lines.append(f"@pytest.mark.parametrize('case_in,expected', [")
            lines.extend(param_rows)
            lines.append("])")
            lines.append(f"def {test_name}(case_in, expected):")
            lines.append(f"    result = target_module.{fn_name}(**case_in)")
            lines.append("    assert result == expected")
            lines.append("")

        # ---- raises cases ----
        for i, rcase in enumerate(raises_cases):
            case_in = rcase.get("in", {})
            exc_type = rcase.get("type", "Exception")
            match = rcase.get("match")

            test_name = f"test_{_safe_ident(fn_name)}_raises_{i+1}"
            lines.append(f"def {test_name}():")
            if match:
                lines.append(f"    with pytest.raises({exc_type}, match={_py_literal(match)}):")
            else:
                lines.append(f"    with pytest.raises({exc_type}):")
            lines.append(f"        target_module.{fn_name}(**{_py_literal(case_in)})")
            lines.append("")

    if len(lines) <= 3:
        lines.append("# No @testai_json specs found to generate tests.")
        lines.append("")

    return "\n".join(lines)

