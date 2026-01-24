# .utils/config_loader.py
from pathlib import Path
import os
import yaml

from research_and_analyst import PROJECT_ROOT

DEFAULT_CONFIG = PROJECT_ROOT / "research_and_analyst" / "config" / "configuration.yaml"

def load_config(config_path: str | None = None) -> dict:
    """
    Resolve config path reliably irrespective of CWD.
    Priority: explicit arg > CONFIG_PATH env > <PROJECT_ROOT>/config/<file>.yaml
    """
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH") or DEFAULT_CONFIG

    path = Path(config_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
