#!/usr/bin/env python3
"""
Interactive model selector for the Zen API.
Fetches available models, lets the user pick one, stores in .agents/model_config.json.
"""

import json
import random
import string
import sys
import urllib.request
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / ".agents" / "model_config.json"
ZEN_URL = "https://opencode.ai/zen/v1/models"


def _zen_session_id() -> str:
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-_"
    return "ses_" + "".join(random.choices(alphabet, k=26))


def fetch_models() -> list[dict]:
    headers = {
        "Authorization": "Bearer public",
        "x-opencode-project": str(uuid.uuid4()),
        "x-opencode-session": _zen_session_id(),
        "x-opencode-request": str(uuid.uuid4()),
        "x-opencode-client": "python-script",
        "User-Agent": "opencode/1.15.4",
    }
    req = urllib.request.Request(ZEN_URL, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data["data"]


def pick_model(models: list[dict]) -> dict:
    free = [m for m in models if m["id"].endswith("-free")]
    paid = [m for m in models if m not in free]
    display_list = free + paid

    print("\nAvailable models:\n")

    if free:
        print("--- Free Tier ---")
        for i, m in enumerate(free, 1):
            print(f"  {i}. {m['id']}")
        print()

    offset = len(free)
    if paid:
        print("--- Paid Tier ---")
        for i, m in enumerate(paid, 1):
            print(f"  {offset + i}. {m['id']}")

    print()
    while True:
        try:
            choice = input("Enter number: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(display_list):
                return display_list[idx]
            print(f"Enter a number between 1 and {len(display_list)}.")
        except ValueError:
            print("Enter a valid number.")


def main():
    try:
        models = fetch_models()
    except Exception as e:
        print(f"Failed to fetch models: {e}", file=sys.stderr)
        sys.exit(1)

    selected = pick_model(models)
    config = {"model": selected["id"]}
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
    print(f"\nSaved model '{selected['id']}' to {CONFIG_PATH}")


if __name__ == "__main__":
    main()
