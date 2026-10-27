# Traefik

Reverse proxy for all stacks. Requests a wildcard certificate for `DOMAIN` and `*.DOMAIN`
from Let's Encrypt with the Cloudflare DNS challenge.

The static configuration is passed as flags in `docker-compose.yml`, `dynamic.yml` is a
Go template rendered with the container environment. All values come from the
environment (see `.env.example`), which Komodo writes per machine, see [komodo/README.md](../komodo/README.md).

The stacks join the external `traefik_backbone` network. On a new machine Komodo creates it
before deploying this stack (`pre_deploy` in `komodo/sync/servers/<server>.toml`).
