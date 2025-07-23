from __future__ import annotations
import os
import tomllib
import tomli_w
from pathlib import Path
from typing import Any, Dict

DEFAULTS: Dict[str, Any] = {
    "buffer_size": 3,
    "count_total": True,
}

def config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "jsonviewer"

def config_path() -> Path:
    return config_dir() / "config.toml"

def load_config() -> Dict[str, Any]:
    p = config_path()
    if not p.exists():
        return DEFAULTS.copy()
    with p.open("rb") as f:
        data = tomllib.load(f)
    # fill missing defaults
    cfg = DEFAULTS.copy()
    cfg.update(data)
    return cfg

def save_config(cfg: Dict[str, Any]) -> None:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    with config_path().open("wb") as f:
        tomli_w.dump(cfg, f)

def set_key(key: str, value: str) -> None:
    cfg = load_config()
    if key not in DEFAULTS:
        raise KeyError(f"Unknown key: {key}. Valid keys: {', '.join(DEFAULTS)}")
    casted = _cast_value(value, type(DEFAULTS[key]))
    cfg[key] = casted
    save_config(cfg)

def get_key(key: str) -> Any:
    cfg = load_config()
    if key not in DEFAULTS:
        raise KeyError(f"Unknown key: {key}. Valid keys: {', '.join(DEFAULTS)}")
    return cfg[key]

def reset_config() -> None:
    save_config(DEFAULTS.copy())

def _cast_value(v: str, t):
    if t is bool:
        return v.lower() in {"1", "true", "yes", "on"}
    if t is int:
        return int(v)
    return v  # str or other
