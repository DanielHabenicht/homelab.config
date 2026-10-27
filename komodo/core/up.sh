#!/bin/sh
# Start (or update) this site's Komodo Core with its settings and secrets:
#   ./up.sh home
set -eu
site=${1:?usage: $0 <site>}
cd "$(dirname "$0")"
export SOPS_AGE_KEY_FILE=${SOPS_AGE_KEY_FILE:-/etc/komodo/age.key}
sops exec-env "../sites/$site/secrets/komodo-core.env" \
  "docker compose --env-file ../sites/$site/core.env up -d"
