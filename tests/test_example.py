import pytest
import importlib.util
from pathlib import Path

MODULE_PATH = Path('example.py').resolve()
spec = importlib.util.spec_from_file_location('target_module', MODULE_PATH)
target_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(target_module)

@pytest.mark.parametrize('case_in,expected', [
    ({'x': 1, 'y': 5}, True),
    ({'x': 2, 'y': 4}, True),
    ({'x': 3, 'y': 10}, False),
    ({'x': 5, 'y': 25}, True),
    ({'x': 0, 'y': 10}, False),
    ({'x': 10, 'y': 10}, True),
])
def test_divisable_cases(case_in, expected):
    result = target_module.divisable(**case_in)
    assert result == expected

def test_divisable_raises_1():
    with pytest.raises(TypeError):
        target_module.divisable(**{'x': 'a', 'y': 10})

def test_divisable_raises_2():
    with pytest.raises(TypeError):
        target_module.divisable(**{'x': 2, 'y': None})

def test_divisable_raises_3():
    with pytest.raises(TypeError):
        target_module.divisable(**{'x': None, 'y': 10})
