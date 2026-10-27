# Komodo

[Komodo](https://komo.do) deploys the stacks of this repository and keeps them up to date from git.
Every site (my place, my parents' place, ...) runs its **own** Komodo, so the sites don't need to
reach each other, but all of them are configured in this repository.

```
komodo/
  stacks/<stack>.toml          how a stack is deployed (shared by all sites)
  sites/<site>/site.toml       the site: its values (DOMAIN, DATA_ROOT, ...), which stacks it runs,
                               the Resource Sync and the deploy procedure
  sites/<site>/core.env        non-secret settings of the site's Komodo Core
  sites/<site>/secrets/*.env   secrets, encrypted with SOPS (one file per stack + komodo-core.env)
  core/                        Komodo Core compose file and up.sh
  import-env.py                turns the old per-stack .env files into secrets/*.env
.sops.yaml                     who can decrypt which site's secrets
```

## How it fits together

- **Komodo Core** (UI, database) and **Periphery** (the agent that runs `docker compose`) run on the site's Docker host.
  Periphery runs with systemd, so it can use `sops` and the site's age key.
- The site's **Resource Sync** reads `komodo/sites/<site>/` and the `komodo/stacks/*.toml` files listed in its
  `resource_path` from GitHub, and creates the stacks and variables in Komodo.
- For every stack Komodo clones this repository into its own folder (`/etc/komodo/stacks/<stack>`), writes the
  non-secret environment from the stack TOML (`[[DOMAIN]]` etc. filled in from the site's variables) to `.env`,
  and runs
  `sops exec-env ../komodo/sites/<site>/secrets/<stack>.env 'docker compose ... up -d'`.
  The secrets only exist in memory of that command, they are never written to disk.
- Komodo may delete that folder at any time, so **no data lives there**. The compose files mount their data from
  `${DATA_ROOT}/<stack>/...` and use `${DOMAIN}` for every host name. Both are required.

## Secrets and disaster recovery

Every `secrets/*.env` is encrypted for two [age](https://age-encryption.org) keys (see [`/.sops.yaml`](../.sops.yaml)):

- **admin key**: mine, kept in the password manager. Can decrypt every site.
- **site key**: `/etc/komodo/age.key` on the site's machine. Can only decrypt that site.

To rebuild a site from scratch you need: this repository, the admin key and the data backup
([`backup/`](../backup/README.md)). Komodo's own database holds nothing that isn't in git.

Edit secrets with `sops edit komodo/sites/<site>/secrets/<stack>.env` (needs one of the two keys), commit and push.

## Automatic updates

Each site has a `deploy-on-push` procedure (in `site.toml`): every 15 minutes it applies the sync and redeploys
the stacks whose compose file, environment or secrets changed. It polls GitHub, so nothing at home has to be
reachable from the internet. (A GitHub webhook to `https://komodo.<domain>/listener/github/procedure/deploy-on-push/main`
works too, if Komodo is reachable.)

Images with rolling tags (`latest`, `release`) are shown as updatable (`poll_for_updates`). Pinned versions are
bumped in git (e.g. with [Renovate](https://docs.renovatebot.com/)), the next poll deploys them.

## Setting up a site

Needed on the machine: Docker, [sops](https://github.com/getsops/sops/releases) (≥ 3.9) and `age`.
The examples use `home`; for another site add `komodo/sites/<site>/` (copy `parents/`) and a rule in `.sops.yaml` first.

### 1. Keys (once per site, plus the admin key once)

```sh
age-keygen -o admin.key                 # only once: store in the password manager, then delete the file
sudo mkdir -p /etc/komodo && sudo age-keygen -o /etc/komodo/age.key && sudo chmod 600 /etc/komodo/age.key
sudo age-keygen -y /etc/komodo/age.key  # public key of this site
```

Put both public keys into `.sops.yaml` and push.

### 2. Komodo Core

```sh
git clone https://github.com/DanielHabenicht/homelab.config.git /opt/homelab && cd /opt/homelab
umask 077
# Secrets of Komodo Core (only once per site, then commit the encrypted file)
cat > komodo/sites/home/secrets/komodo-core.env <<EOF
KOMODO_DATABASE_USERNAME=komodo
KOMODO_DATABASE_PASSWORD=$(openssl rand -hex 24)
KOMODO_INIT_ADMIN_PASSWORD=$(openssl rand -hex 12)
KOMODO_WEBHOOK_SECRET=$(openssl rand -hex 32)
KOMODO_JWT_SECRET=$(openssl rand -hex 32)
EOF
sops encrypt --in-place komodo/sites/home/secrets/komodo-core.env

docker network inspect traefik_backbone >/dev/null 2>&1 || docker network create --internal traefik_backbone
sudo komodo/core/up.sh home
```

Open `http://<machine>:9120` (later `https://komodo.<domain>`), log in as `admin`
(`sops decrypt komodo/sites/home/secrets/komodo-core.env` shows the password) and change the password.

### 3. Periphery

In Komodo: *Settings → Onboarding → New onboarding key*. Then:

```sh
curl -sSL https://raw.githubusercontent.com/moghtech/komodo/main/scripts/setup-periphery.py \
  | sudo python3 - --core-address="ws://127.0.0.1:9120" --connect-as="local" --onboarding-key="O-..."
sudo systemctl enable periphery
```

The server `local` shows up as *OK*.

### 4. Resource Sync (once, afterwards it manages itself)

*Syncs → New Resource Sync*, name `homelab`, mode *Git Repo*, repo `DanielHabenicht/homelab.config`,
branch `main`, resource path `komodo/sites/home`, enable *Include Variables*. Save, *Refresh*, *Execute*.
The next execution picks up the full `resource_path` from `site.toml`, so run *Refresh* and *Execute* once more.

Now the variables, stacks and the `deploy-on-push` procedure exist.

### 5. Secrets of the stacks

Every stack listed in `site.toml` that has a `compose_cmd_wrapper` needs `secrets/<stack>.env`
(the comment in `komodo/stacks/<stack>.toml` lists the keys):

```sh
sops edit komodo/sites/home/secrets/<stack>.env    # creates the file encrypted
```

For the existing machine `import-env.py` does that from the old `.env` files, see below.

### 6. Deploy

Deploy `traefik` first, then the rest. With `schedule_enabled = true` in `site.toml` the procedure does it
(and keeps doing it on every change).

## Migrating the existing machine (home)

Today the stacks run from the git checkout in `/mnt/data/homelab`, each with a `.env` next to it. That folder
becomes `DATA_ROOT`: **the data does not move**. Komodo deploys every stack with the same compose project name
(`project_name` in `komodo/stacks/*.toml`), the same bind mounts and the same named volumes, so it takes over the
running containers.

Keep `/mnt/data/homelab` on its current commit until you are done (don't `git pull` there). Then rolling back a
stack is `cd /mnt/data/homelab/<stack> && docker compose up -d`.

1. **Rotate the Pocket ID client secrets** of actual-budget, gramps, tandoor-recipes and trilium. They were committed
   to this public repository.
2. `docker compose ls`: the project names must match `project_name` in `komodo/stacks/*.toml`
   (the folder name, `unifi-network-application` for ubiquiti).
3. Steps 1-4 of *Setting up a site* above. `home/site.toml` has `schedule_enabled = false`, so nothing is
   deployed automatically yet.
4. Secrets from the old `.env` files:
   ```sh
   cd /opt/homelab
   python3 komodo/import-env.py home /mnt/data/homelab            # dry run, shows which keys go where
   python3 komodo/import-env.py home /mnt/data/homelab --write    # writes secrets/<stack>.env, encrypted
   ```
   It lists what needs a look: empty values to fill in with `sops edit` (the rotated OIDC secrets), old keys the
   compose files don't use anymore and values that differ from the stack TOML. Commit and push the files.
5. Move the stacks one by one, `traefik` and `pocketid` last: open the stack in Komodo, check *Info*, *Deploy*,
   check the app. If something is wrong, roll back as above.
6. When everything runs from Komodo, set `schedule_enabled = true` in `komodo/sites/home/site.toml` and push.
   (Not earlier: the procedure also deploys stacks that were never deployed by Komodo.)

`/mnt/data/homelab` then only holds data. Delete the old `.env` files once you no longer need a rollback.

## Adding a site (e.g. parents)

1. Adjust `komodo/sites/parents/site.toml` (domain, data folder, which stacks) and `core.env`.
2. DNS: `<domain>` and `*.<domain>` to the machine's IP in the local network there (Traefik gets the certificate
   via the Cloudflare DNS challenge, nothing needs to be reachable from outside).
3. *Setting up a site* above, with `parents` instead of `home`. New random values for its secrets, new Pocket ID
   clients for its apps.
