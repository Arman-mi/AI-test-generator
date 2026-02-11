from pathlib import Path

from test_ai.languages.python.discover import discover_functions
from test_ai.languages.python.spec_extract import extract_testai_json
from test_ai.languages.python.render_pytest import render_pytest_for_module



def module_name_from_path(path: str) -> str:
    return Path(path).stem  # "example.py" -> "example"


def main():
    target = "example.py"  # change this as needed
    mod = Path(target).stem
    


    funcs = discover_functions(target)

    discovered_payload = []
    for f in funcs:
        spec = extract_testai_json(f.docstring)
        if spec is None:
            print(f"Warning: {f.name} has no @testai_json block; skipping.")
            continue

        discovered_payload.append({
            "name": f.name,
            "args": f.args,
            "spec": spec,
        })

    test_text = render_pytest_for_module(target, discovered_payload)


    out_dir = Path("tests")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"test_{mod}.py"


    out_path.write_text(test_text, encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
