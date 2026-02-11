import pytest
import importlib.util
from pathlib import Path

MODULE_PATH = Path('example.py').resolve()
spec = importlib.util.spec_from_file_location('target_module', MODULE_PATH)
target_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(target_module)

@pytest.mark.parametrize('case_in,expected', [
    ({'x': 2}, True),
    ({'x': 3}, False),
    ({'x': 0}, True),
])
def test_is_even_cases(case_in, expected):
    result = target_module.is_even(**case_in)
    assert result == expected
