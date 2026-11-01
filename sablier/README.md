# Sablier

[Sablier](https://github.com/sablierapp/sablier) scales rarely used stacks to
zero and starts them again on the first request. Traefik shows a waiting page
while the containers boot, and Sablier stops them again after the session
expires (no request for `sessionDuration`).

Currently on demand: **Gramps**, **Tandoor** (web only) and **Monica** (app
only). Immich and everything else stays always on.

The Tandoor and Monica databases stay always on, because the backup job runs
`pg_dumpall` / `mariadb-dump` inside them and would fail if they were
stopped. They are small, the app containers are where the RAM goes.

## Setup

1. Start Sablier: `docker compose up -d` (in this folder)
2. Recreate Traefik so it loads the plugin (needs internet to download it on
   start): `docker compose up -d --force-recreate` in `../traefik`
3. Recreate the on-demand stacks: `docker compose up -d` in `../gramps`,
   `../tandoor-recipes` and `../monica`

Sablier stops the on-demand containers right away when it starts and wakes
them on the next request.

## Putting another stack on demand

Requires Traefik v3.6+ (`traefik.docker.allownonrunning`), so Traefik keeps
the route while the container is stopped.

On **every** container of the stack (app, workers, redis, ...). Leave out
databases that the backup job dumps with `docker-volume-backup.archive-pre`:

```yaml
labels:
  - "sablier.enable=true"
  - "sablier.group=<app>"
```

On the container that Traefik routes to, additionally:

```yaml
labels:
  - "traefik.docker.allownonrunning=true"
  - "traefik.http.routers.<app>.middlewares=<app>-sablier"
  - "traefik.http.middlewares.<app>-sablier.plugin.sablier.sablierUrl=http://sablier:10000"
  - "traefik.http.middlewares.<app>-sablier.plugin.sablier.group=<app>"
  - "traefik.http.middlewares.<app>-sablier.plugin.sablier.sessionDuration=30m"
  - "traefik.http.middlewares.<app>-sablier.plugin.sablier.dynamic.displayName=<App>"
```

Give the routed container a `healthcheck`. Sablier waits for it to be
healthy before sending the user on, otherwise the first page load can hit a
502 while the app is still booting.

Use `restart: unless-stopped` (not `always`), so Docker does not bring the
containers back after a daemon restart.

Don't put stacks on demand that do background work on their own (Immich
jobs, Paperless consumer, Dawarich imports), they only run while awake.
