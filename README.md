# My HomeLab Setup

All services are running in docker containers, reverse proxied by Traefik.

No kubernetes magic here, just plain old docker-compose, deployed by [Komodo](komodo/README.md).
Every site (my place, my parents' place) runs its own Komodo, all configured from this repository,
each with its own domain, data folder and SOPS-encrypted secrets.

Hopefully more secure by not allowing the services to access the internet.

## Layout

- `<stack>/docker-compose.yml`: one folder per stack. Every machine-specific value comes from the environment:
  - `DOMAIN`: services are served at `<name>.${DOMAIN}`, e.g. `photos.home.aquiver.de`
  - `DATA_ROOT`: data is stored in `${DATA_ROOT}/<stack>/`, e.g. `/mnt/data/homelab/immich/library`
  - secrets, e.g. `OIDC_CLIENT_SECRET`, from `komodo/sites/<site>/secrets/<stack>.env` (encrypted)
- [`komodo/`](komodo/README.md): which stacks run on which site, with which values and secrets,
  how to set up a site and how to recover one.
- [`backup/`](backup/README.md): nightly encrypted backups of the stack data.

## Services

- [Traefik](https://traefik.io/)

TODO:

https://docs.n8n.io/
