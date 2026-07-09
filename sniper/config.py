import os
from dataclasses import dataclass
from typing import Optional


def _get_env_or_fail(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise ValueError(f"missing required env var: {key}")
    return val.strip()


