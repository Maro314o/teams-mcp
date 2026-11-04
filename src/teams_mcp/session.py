"""Posizione e stato della futura sessione locale."""

import os
from pathlib import Path


def session_path() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home) if data_home and Path(data_home).is_absolute() else Path.home() / ".local" / "share"
    return base / "teams-mcp" / "session.json"


def session_status() -> dict[str, bool]:
    return {"configured": session_path().is_file()}
