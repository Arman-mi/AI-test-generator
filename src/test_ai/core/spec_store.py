from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SidecarSpec:
    version: int
    target: str
    functions: Dict[str, Dict[str, Any]]  # fn_name -> {"cases":[...], "raises":[...]}


def spec_path_for_target(target_path: str | Path) -> Path:
    p = Path(target_path)
    return Path("tests") / f"{p.stem}.testai.json"


def load_sidecar(path: Path) -> Optional[SidecarSpec]:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Sidecar spec must be a JSON object")
    if data.get("version") != 1:
        raise ValueError(f"Unsupported spec version: {data.get('version')}")
    functions = data.get("functions", {})
    if not isinstance(functions, dict):
        raise ValueError("'functions' must be an object")
    return SidecarSpec(version=1, target=str(data.get("target", "")), functions=functions)


def save_sidecar(path: Path, spec: SidecarSpec) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": spec.version,
        "target": spec.target,
        "functions": spec.functions,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
