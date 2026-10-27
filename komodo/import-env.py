#!/usr/bin/env python3
"""Import the existing per-stack .env files into Komodo secret variables.

Run on the machine where the stacks currently run, from this repository:

    export KOMODO_URL=https://komodo.home.aquiver.de
    export KOMODO_API_KEY=K-...  KOMODO_API_SECRET=S-...   # Settings -> Api Keys
    python3 komodo/import-env.py home /mnt/data/homelab              # dry run
    python3 komodo/import-env.py home /mnt/data/homelab --apply      # create secrets

For every stack in komodo/sync/servers/<server>.toml it reads
<old-checkout>/<run_directory>/.env and, for every line `KEY = [[VAR]]` in the
stack environment, stores the old value of KEY as secret variable VAR.
Existing variables are only overwritten with --overwrite.

It also reports what needs a manual look:
  - secrets the stack needs but the old .env does not have (create them in the UI)
  - keys in the old .env that the new stack environment does not set
  - literal values in the TOML that differ from the old .env
"""

import argparse
import json
import os
import re
import sys
import tomllib
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VAR_REF = re.compile(r"^\[\[([A-Za-z0-9_]+)\]\]$")
# Keys that are no longer needed in the environment, (stack, key): hint
MOVED = {
    ("immich", "UPLOAD_LOCATION"): "replaced by ${DATA_ROOT}/immich/library, make sure that is the same folder",
    ("immich", "DB_DATA_LOCATION"): "replaced by ${DATA_ROOT}/immich/postgres, make sure that is the same folder",
    ("pocketid", "APP_URL"): "now set in docker-compose.yml",
    ("pocketid", "TRUST_PROXY"): "now set in docker-compose.yml",
}


def parse_env(text):
    """Parse `KEY=value` / `KEY = value` lines (Komodo and docker .env style)."""
    env = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        env[key] = value
    return env


def komodo(path, request, params):
    req = urllib.request.Request(
        f"{os.environ['KOMODO_URL'].rstrip('/')}/{path}/{request}",
        data=json.dumps(params).encode(),
        headers={
            "content-type": "application/json",
            "x-api-key": os.environ["KOMODO_API_KEY"],
            "x-api-secret": os.environ["KOMODO_API_SECRET"],
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as res:
        return json.load(res)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("server", help="server name, e.g. home")
    parser.add_argument("old_checkout", type=Path, help="folder with the old <stack>/.env files")
    parser.add_argument("--apply", action="store_true", help="create the variables in Komodo")
    parser.add_argument("--overwrite", action="store_true", help="also update existing variables")
    args = parser.parse_args()

    toml_path = REPO / "komodo" / "sync" / "servers" / f"{args.server}.toml"
    stacks = tomllib.loads(toml_path.read_text())["stack"]
    declared = {v["name"] for v in tomllib.loads((REPO / "komodo" / "sync" / "variables.toml").read_text())["variable"]}

    to_create = {}
    notes = []
    for stack in stacks:
        cfg = stack["config"]
        env_file = args.old_checkout / cfg["run_directory"] / ".env"
        old = parse_env(env_file.read_text()) if env_file.exists() else {}
        new = parse_env(cfg.get("environment", ""))
        name = stack["name"]

        for key, value in new.items():
            ref = VAR_REF.match(value)
            if ref is None:
                if key in old and old[key] != value:
                    notes.append(f"{name}: {key} is '{value}' in the TOML but '{old[key]}' in {env_file}")
            elif ref.group(1) in declared:
                continue
            elif key in old:
                to_create[ref.group(1)] = old[key]
            else:
                notes.append(f"{name}: no {key} in {env_file}, create secret {ref.group(1)} in the UI")
        for key in sorted(old.keys() - new.keys()):
            hint = MOVED.get((cfg["run_directory"], key))
            if hint:  # only paths and URLs, safe to print
                notes.append(f"{name}: {key}={old[key]} from {env_file} {hint}")
            else:
                notes.append(f"{name}: {key} from {env_file} is not set anymore (add it to the TOML if still needed)")

    existing = set()
    if args.apply:
        existing = {v["name"] for v in komodo("read", "ListVariables", {})}

    print(f"Secrets from the old .env files ({len(to_create)}):")
    for var, value in sorted(to_create.items()):
        if var in existing and not args.overwrite:
            print(f"  skip    {var} (exists)")
            continue
        if args.apply:
            if var in existing:
                komodo("write", "UpdateVariableValue", {"name": var, "value": value})
            else:
                komodo("write", "CreateVariable", {"name": var, "value": value, "is_secret": True})
        print(f"  {'set' if args.apply else 'would set'} {var}")

    if notes:
        print(f"\nCheck by hand ({len(notes)}):")
        for note in notes:
            print(f"  - {note}")
    if not args.apply:
        print("\nDry run, nothing was changed. Add --apply to create the secrets.")


if __name__ == "__main__":
    sys.exit(main())
