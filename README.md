# My HomeLab Setup

All services are running in docker containers on a single host.
They are reverse proxied by Traefik.

No kubernetes magic here, just plain old docker-compose.

Hopefully more secure by not allowing the services to access the internet. 

## Services

- [Traefik](https://traefik.io/)
