from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


def _safe_ident(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "x"


def _py_literal(value: Any) -> str:
    return repr(value)


def render_pytest_for_module(
    module_path: str,
    specs_by_function: Dict[str, Dict[str, Any]],
) -> str:
    lines: List[str] = []
    lines.append("import pytest")
    lines.append("import importlib.util")
    lines.append("from pathlib import Path")
    lines.append("")
    lines.append(f"MODULE_PATH = Path({repr(str(Path(module_path).resolve()))})")
    lines.append("spec = importlib.util.spec_from_file_location('target_module', MODULE_PATH)")
    lines.append("target_module = importlib.util.module_from_spec(spec)")
    lines.append("assert spec and spec.loader")
    lines.append("spec.loader.exec_module(target_module)")
    lines.append("")

    any_tests = False

    for fn_name, spec_obj in specs_by_function.items():
        cases = spec_obj.get("cases", []) or []
        raises_cases = spec_obj.get("raises", []) or []

        if cases:
            any_tests = True
            param_rows: List[str] = []
            for case in cases:
                case_in = case.get("in", {})
                expected = case.get("out", None)
                param_rows.append(f"    ({_py_literal(case_in)}, {_py_literal(expected)}),")

            test_name = f"test_{_safe_ident(fn_name)}_cases"
            lines.append("@pytest.mark.parametrize('case_in,expected', [")
            lines.extend(param_rows)
            lines.append("])")
            lines.append(f"def {test_name}(case_in, expected):")
            lines.append(f"    result = target_module.{fn_name}(**case_in)")
            lines.append("    assert result == expected")
            lines.append("")

        for i, rcase in enumerate(raises_cases):
            any_tests = True
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

    if not any_tests:
        lines.append("# No specs found to generate tests.")
        lines.append("")

    return "\n".join(lines)
