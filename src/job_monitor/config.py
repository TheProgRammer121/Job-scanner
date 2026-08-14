from __future__ import annotations

import json
import os
from pathlib import Path

from .models import Company


def load_dotenv(path: str | Path = ".env") -> None:
    env = Path(path)
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def list_value(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


def load_companies(path: str | Path = "companies.json") -> list[Company]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Company(None, item["name"], item["url"], item.get("enabled", True), int(item.get("priority", 1))) for item in raw]
