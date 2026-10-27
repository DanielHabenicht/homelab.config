#!/usr/bin/env python3
"""Turn the existing per-stack .env files into SOPS-encrypted secret files.

Run on the machine where the stacks currently run, from this repository
(sops installed, .sops.yaml filled in with the public keys):

    python3 komodo/import-env.py home /mnt/data/homelab            # dry run
    python3 komodo/import-env.py home /mnt/data/homelab --write    # write the files

For every stack of the site (resource_path in komodo/sites/<site>/site.toml) it
writes komodo/sites/<site>/secrets/<stack>.env, encrypted with sops. It contains
every variable the stack's docker-compose.yml uses that is not already set in the
stack's Komodo environment (komodo/stacks/<stack>.toml), with the value from
<old-checkout>/<stack>/.env. Variables the compose file requires but the old
.env does not have are written empty: fill them in with
`sops edit komodo/sites/<site>/secrets/<stack>.env`.

Values are never printed. Existing secret files are only replaced with --overwrite.
"""

import argparse
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# ${VAR}, ${VAR:?msg}, ${VAR:-default}; group 2 is set if the variable has a default
COMPOSE_VAR = re.compile(r"\$\{([A-Za-z0-9_]+)(:?-)?[^}]*\}")
# Set by Komodo for every stack, see komodo/stacks/*.toml
KOMODO_VARS = {"DOMAIN", "DATA_ROOT"}
# Keys of the old .env files that are not needed anymore, (stack, key): hint
MOVED = {
    ("immich", "UPLOAD_LOCATION"): "replaced by ${DATA_ROOT}/immich/library, make sure that is the same folder",
    ("immich", "DB_DATA_LOCATION"): "replaced by ${DATA_ROOT}/immich/postgres, make sure that is the same folder",
    ("pocketid", "APP_URL"): "now set in docker-compose.yml",
    ("pocketid", "TRUST_PROXY"): "now set in docker-compose.yml",
    ("paperless-ngx", "SUBDOMAIN"): "replaced by DOMAIN",
    ("traefik", "SUBDOMAIN"): "replaced by DOMAIN",
    ("pocketid", "SUBDOMAIN"): "replaced by DOMAIN",
    ("trilium", "SUBDOMAIN"): "replaced by DOMAIN",
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


def site_stacks(site):
    sync = tomllib.loads((REPO / "komodo" / "sites" / site / "site.toml").read_text())["resource_sync"][0]
    for path in sync["config"]["resource_path"]:
        if path.startswith("komodo/stacks/"):
            yield tomllib.loads((REPO / path).read_text())["stack"][0]


def write_encrypted(path, env):
    """Write the dotenv file with mode 0600 and encrypt it in place."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("".join(f"{k}={v}\n" for k, v in env.items()))
    try:
        subprocess.run(["sops", "encrypt", "--in-place", str(path)], check=True, cwd=REPO)
    except (OSError, subprocess.CalledProcessError):
        path.unlink()  # never leave a plaintext file behind
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("site", help="folder name in komodo/sites, e.g. home")
    parser.add_argument("old_checkout", type=Path, help="folder with the old <stack>/.env files")
    parser.add_argument("--write", action="store_true", help="write and encrypt the secret files")
    parser.add_argument("--overwrite", action="store_true", help="replace existing secret files")
    args = parser.parse_args()

    notes = []
    for stack in site_stacks(args.site):
        cfg = stack["config"]
        name, run_dir = stack["name"], cfg["run_directory"]
        compose = (REPO / run_dir / cfg["file_paths"][0]).read_text()
        used = {}  # variable -> required (no default)
        for var, default in COMPOSE_VAR.findall(compose):
            used[var] = used.get(var, False) or not default
        komodo_env = KOMODO_VARS | set(parse_env(cfg.get("environment", "")))
        env_file = args.old_checkout / run_dir / ".env"
        old = parse_env(env_file.read_text()) if env_file.exists() else {}

        secrets = {k: old[k] for k in sorted(used) if k in old and k not in komodo_env}
        missing = sorted(k for k, required in used.items() if required and k not in komodo_env and k not in old)
        secrets.update({k: "" for k in missing})

        for key in sorted(old.keys() - used.keys() - komodo_env):
            hint = MOVED.get((run_dir, key), "not used by docker-compose.yml anymore, map it there if the app needs it")
            notes.append(f"{name}: {key} from the old .env: {hint}")
        for key in sorted(old.keys() & komodo_env - KOMODO_VARS):
            if old[key] != parse_env(cfg["environment"])[key]:
                notes.append(f"{name}: {key} differs between the old .env and komodo/stacks/{name}.toml")

        has_wrapper = bool(cfg.get("compose_cmd_wrapper"))
        if not secrets:
            if has_wrapper:
                notes.append(f"{name}: has a sops wrapper but no secrets, remove compose_cmd_wrapper")
            print(f"{name:20} no secrets")
            continue
        if not has_wrapper:
            notes.append(f"{name}: needs secrets but has no compose_cmd_wrapper in komodo/stacks/{name}.toml")

        target = REPO / "komodo" / "sites" / args.site / "secrets" / f"{name}.env"
        rel = target.relative_to(REPO)
        summary = ", ".join(secrets) + (f"  (empty: {', '.join(missing)})" if missing else "")
        if target.exists() and not args.overwrite:
            print(f"{name:20} {rel} exists, skipped")
        elif args.write:
            write_encrypted(target, secrets)
            print(f"{name:20} wrote {rel}: {summary}")
        else:
            print(f"{name:20} would write {rel}: {summary}")
        if missing:
            notes.append(f"{name}: fill in {', '.join(missing)} with `sops edit {rel}`")

    if notes:
        print(f"\nCheck by hand ({len(notes)}):")
        for note in notes:
            print(f"  - {note}")
    if not args.write:
        print("\nDry run, nothing was written. Add --write to create the encrypted files.")


if __name__ == "__main__":
    sys.exit(main())
