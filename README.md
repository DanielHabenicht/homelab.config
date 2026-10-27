# My HomeLab Setup

All services are running in docker containers, reverse proxied by Traefik.

No kubernetes magic here, just plain old docker-compose, deployed by [Komodo](komodo/README.md)
to one or more machines (each with its own domain, data folder and secrets).

Hopefully more secure by not allowing the services to access the internet.

## Layout

- `<stack>/docker-compose.yml`: one folder per stack. Every machine-specific value comes from the environment:
  - `DOMAIN`: services are served at `<name>.${DOMAIN}`, e.g. `photos.home.aquiver.de`
  - `DATA_ROOT`: data is stored in `${DATA_ROOT}/<stack>/`, e.g. `/mnt/data/homelab/immich/library`
  - secrets, e.g. `OIDC_CLIENT_SECRET`
- [`komodo/`](komodo/README.md): which stacks run on which machine, with which values, and how to set up a new machine.
- [`backup/`](backup/README.md): nightly encrypted backups of the stack data.

## Services

- [Traefik](https://traefik.io/)

TODO:

https://docs.n8n.io/
