# Dawarich

[Dawarich](https://dawarich.app/) keeps your location history on your own
server (a Google Maps Timeline replacement): map, trips, visits, stats.

Runs at https://timeline.home.aquiver.de, always on (not with Sablier).

## Setup

1. In Pocket ID, add an OIDC client "Dawarich" with the callback URL
   `https://timeline.home.aquiver.de/users/auth/openid_connect/callback`.
2. `cp .env.example .env`, fill in the database password, `SECRET_KEY_BASE`
   (`openssl rand -hex 64`) and the Pocket ID client id/secret.
3. `docker compose up -d`. The first start runs the migrations and takes a
   few minutes.
4. Dawarich creates an admin on first start: `demo@dawarich.app` /
   `safepassword`. Log in with it and, under *Account*, change the e-mail to
   the one in your Pocket ID profile and set a new password.
5. Log out and use *Sign in with Pocket ID*. Dawarich asks for your Dawarich
   password once to link the two accounts.
6. Set `ALLOW_EMAIL_PASSWORD_LOGIN=false` in `.env` and run
   `docker compose up -d` again.

Pocket ID has to send `email_verified: true` for the linking step. If it
refuses with "e-mail not verified", mark the e-mail as verified for your user
in Pocket ID.

New users don't sign up on their own (`OIDC_AUTO_REGISTER=false`). Create them
as admin in Dawarich with their Pocket ID e-mail; they link the same way.

## Recording locations

Get your API key under *Account* and set up one of the apps:

- **Dawarich** app (iOS / Android)
- [OwnTracks](https://dawarich.app/docs/tutorials/track-your-location#owntracks) (HTTP mode)
- [Overland](https://dawarich.app/docs/tutorials/track-your-location#overland) (iOS)

The phone has to reach `timeline.home.aquiver.de`, same as the other apps.

## Importing

Google Takeout (Timeline / `Records.json`), GPX, GeoJSON, OwnTracks and more
can be uploaded under *Imports*. Large files can also be dropped into
`watched/<your e-mail>/` on the host, they are picked up automatically.

## Reverse geocoding

Off by default, so no location leaves the homelab. Without it, visits have no
place names. To turn it on, set `PHOTON_API_HOST` in `docker-compose.yml`
(public `photon.komoot.io`, or a self-hosted Photon).

## Backup

Covered by `../backup`: `pg_dumpall` into `db-dump/dawarich.sql` plus
`storage/` (imports, exports). `SECRET_KEY_BASE` is in `.env` and not backed
up, keep a copy somewhere else.

Restore: start only `dawarich_db` with an empty `postgres/`, pipe
`dawarich.sql` into `psql -U dawarich`, copy `storage/` back, then start the
rest.
