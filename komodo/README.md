# Komodo

[Komodo](https://komo.do) deploys the stacks of this repository to every machine (mine, my parents', ...)
and keeps them up to date from git.

- **Komodo Core** (web UI, API) runs once, on `home`: [`core/compose.yaml`](core/compose.yaml).
- **Periphery** (agent) runs on every machine and connects *out* to Core, so no ports need to be opened at the other places.
- **What runs where** is declared in [`sync/`](sync) and applied by a Resource Sync:
  - [`sync/servers/<server>.toml`](sync/servers): the machine and its stacks, with the stack environment.
  - [`sync/variables.toml`](sync/variables.toml): non-secret values per machine (`HOME_DOMAIN`, `HOME_DATA_ROOT`, ...).
  - [`sync/sync.toml`](sync/sync.toml): the sync itself and the `deploy-on-push` procedure.
- **Secrets** are secret variables in the Komodo UI (*Settings → Variables*), named `<SERVER>_<STACK>_<KEY>`,
  e.g. `HOME_IMMICH_DB_PASSWORD`. This repository is public, so they are never in git.

## How a deployment works

Komodo clones this repository for every stack into its own folder (`/etc/komodo/stacks/<stack>`),
writes the stack's `environment` (with `[[VARIABLES]]` filled in) to `.env` next to the compose file
and runs `docker compose -p <project_name> up -d`.

Komodo may delete and re-clone that folder at any time, so **no data lives there**. Every compose
file mounts its data from `${DATA_ROOT}/<stack>/...` instead (e.g. `/mnt/data/homelab/immich/library`),
and the domain comes from `${DOMAIN}`. Both are required, a stack does not start without them.

## Automatic updates

| What changes | What happens |
| --- | --- |
| Push to `main` (compose file, `sync/*.toml`) | GitHub webhook → procedure `deploy-on-push` → applies the sync, then redeploys only the stacks whose files or environment changed. |
| New image for a rolling tag (`latest`, `release`, ...) | `poll_for_updates` shows it in the UI. The built-in *Global Auto Update* procedure (daily) only redeploys stacks with `auto_update = true`. |
| Pinned image versions | Not automatic. Bump them in git (e.g. with [Renovate](https://docs.renovatebot.com/)), the push redeploys. |

The webhook needs GitHub to reach `https://komodo.<domain>/listener/...`. If Komodo is only reachable
at home, either expose just the `/listener` path (e.g. Cloudflare Tunnel, Tailscale Funnel) or use the
schedule of `deploy-on-push` instead (`schedule_enabled = true` in `sync/sync.toml`, every 15 minutes).

## Migrating the existing machine

Today the stacks run from the git checkout in `/mnt/data/homelab`, each with a `.env` next to it.
That folder becomes `DATA_ROOT`: the data stays exactly where it is, only the compose files come from
Komodo's clone afterwards. Mounts and named volumes resolve to the same paths and names as before,
so Komodo takes over the running containers instead of starting new ones.

Keep `/mnt/data/homelab` on its current commit until the migration is done (don't `git pull` there).
Then rolling back a stack is just `cd /mnt/data/homelab/<stack> && docker compose up -d`.

### 0. Before you start

- **Rotate the Pocket ID client secrets** of actual-budget, gramps, tandoor-recipes and trilium.
  They were committed to this public repository. Create new secrets in Pocket ID; they go into Komodo in step 4.
- Make sure the last backup run worked.
- `docker compose ls`: the project names must match `project_name` in [`sync/servers/home.toml`](sync/servers/home.toml)
  (it is the folder name, except `unifi-network-application` for `ubiquiti`). Fix the TOML if one differs.

### 1. Komodo Core

```sh
git clone https://github.com/DanielHabenicht/homelab.config.git /opt/homelab
cd /opt/homelab/komodo/core
cp .env.example .env    # fill in the secrets (openssl rand -hex 32)
docker compose up -d
```

Open `https://komodo.home.aquiver.de`, log in with `KOMODO_INIT_ADMIN_*` and change the password.

### 2. Periphery on `home`

In Komodo: *Settings → Onboarding → New onboarding key*. Then on the machine:

```sh
curl -sSL https://raw.githubusercontent.com/moghtech/komodo/main/scripts/setup-periphery.py \
  | python3 - --core-address="ws://127.0.0.1:9120" --connect-as="home" --onboarding-key="O-..."
sudo systemctl enable periphery
```

The server `home` shows up as *OK* in the UI.

### 3. Resource Sync

*Syncs → New Resource Sync*, name `homelab`, mode *Git Repo*, repo `DanielHabenicht/homelab.config`,
branch `main`, resource path `komodo/sync`, enable *Include Variables*. Save, *Refresh*, check the
pending changes and *Execute*.

This creates the variables, the 15 stacks `home-*` and the `deploy-on-push` procedure.
Nothing is deployed yet. From now on the sync manages itself from [`sync/sync.toml`](sync/sync.toml).

### 4. Secrets

Create an API key (in your user profile in Komodo), then import the existing `.env` files:

```sh
cd /opt/homelab
export KOMODO_URL=https://komodo.home.aquiver.de KOMODO_API_KEY=K-... KOMODO_API_SECRET=S-...
python3 komodo/import-env.py home /mnt/data/homelab            # dry run, shows what it would do
python3 komodo/import-env.py home /mnt/data/homelab --apply
```

For every `KEY = [[HOME_..._KEY]]` in a stack environment it stores the value of `KEY` from the old
`<stack>/.env` as secret variable. It lists what needs a manual look:

- **missing secrets**: create them in *Settings → Variables* (check *secret*). Expected:
  the rotated `*_OIDC_CLIENT_ID` / `*_OIDC_CLIENT_SECRET` for actual-budget, gramps, tandoor-recipes and
  trilium (and paperless-ngx if its `.env` uses other names).
- **keys from the old `.env` that are not set anymore**: add a line to the stack's `environment` in
  `home.toml` if the app still needs it (and the secret, if it is one), or ignore it if it moved into
  the compose file (the script says so).
- **values that differ**: fix the TOML.

Push TOML changes to `main` and run the sync again.

### 5. Move the stacks, one at a time

For each stack, starting with something unimportant (e.g. `home-bonds`) and with `home-traefik` and
`home-pocketid` last:

1. Open the stack in Komodo, check *Info* (the compose file and the `.env` it will write).
2. *Deploy*. Compose recreates the containers of the same project with the same data.
3. Check the app. If something is wrong: `cd /mnt/data/homelab/<stack> && docker compose up -d` brings back the old version.

### 6. Switch on automatic deploys

When every stack is deployed from Komodo:

- GitHub → *Settings → Webhooks → Add webhook*: payload URL
  `https://komodo.home.aquiver.de/listener/github/procedure/deploy-on-push/main`,
  content type `application/json`, secret `KOMODO_WEBHOOK_SECRET` from `core/.env`, *Just the push event*.
  Or set `schedule_enabled = true` in `sync/sync.toml` instead.
- Don't do this earlier: `deploy-on-push` deploys every stack that was never deployed by Komodo.

`/mnt/data/homelab` now only holds data. The git files in it are not used anymore; keep the `.env`
files until you no longer need a rollback.

## Adding another machine

1. Copy [`sync/servers/parents.toml.example`](sync/servers/parents.toml.example) to `sync/servers/<name>.toml`,
   keep the stacks you want and add `<NAME>_DOMAIN` and `<NAME>_DATA_ROOT` to `sync/variables.toml`.
2. Create the `<NAME>_*` secrets in the UI (new random values; new Pocket ID clients if the apps use SSO).
3. DNS: point `<domain>` and `*.<domain>` to the machine (the Cloudflare token needs access to the zone).
4. Install Docker and Periphery on the machine, connecting to Core over the internet or a VPN like Tailscale:
   ```sh
   curl -sSL https://raw.githubusercontent.com/moghtech/komodo/main/scripts/setup-periphery.py \
     | python3 - --core-address="https://komodo.home.aquiver.de" --connect-as="<name>" --onboarding-key="O-..."
   ```
5. Push to `main`. The sync creates the stacks, deploy them once by hand (`<name>-traefik` first),
   afterwards pushes redeploy them automatically.

The compose files are shared. If a machine needs something different, use a variable with a default
(`${VAR:-default}`) rather than copying the compose file.
