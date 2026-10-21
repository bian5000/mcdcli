"""Token resolution with priority: --token flag > MCD_TOKEN env > ~/.mcdcli/config.json."""
import json
import os

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".mcdcli")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def resolve_token(flag_token: str | None = None) -> str | None:
    if flag_token:
        return flag_token
    env = os.environ.get("MCD_TOKEN")
    if env:
        return env
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f).get("token")
    except (OSError, ValueError):
        return None


def save_token(token: str) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"token": token}, f)
