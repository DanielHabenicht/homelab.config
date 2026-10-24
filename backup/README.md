# Backup

Automated backups of all stacks with [offen/docker-volume-backup](https://offen.github.io/docker-volume-backup/),
written to an SMB share and encrypted with [age](https://age-encryption.org/).

- Every file in `conf.d/` is one backup job (one archive per stack, e.g. `pocketid-2026-10-25T03-00-00.tar.gz.age`).
- Daily at 03:00 (`Europe/Berlin`), archives older than 14 days are deleted. Immich runs weekly and keeps 28 days.
- Jobs with the same schedule run one after another.
- Containers labeled `docker-volume-backup.stop-during-backup=<stack>` are stopped while their stack is archived
  (databases, SQLite files) and started again afterwards.
- Bind-mounted stacks are archived as the whole directory, including the gitignored `.env` files and secrets.

## Setup

1. Install the CIFS tools on the Docker host: `sudo apt install cifs-utils`
2. `cp .env.example .env` and fill in the share and the age passphrase.
   Use the IP address of the NAS for `SMB_HOST`. Store the passphrase outside the homelab, without it the backups are useless.
3. Recreate the stacks so the new labels are applied (`docker compose up -d` in every changed stack directory).
4. `docker compose up -d` in this directory.

The SMB share is mounted by Docker when the container starts. If the share is not reachable at that time,
the container does not start (and no backups run) until you run `docker compose up -d` here again.
If the share disappears later, the runs fail and show up in `docker compose logs backup`.
To get notified about failures, set `NOTIFICATION_URLS` (see the [docs](https://offen.github.io/docker-volume-backup/reference/))
and remove `network_mode: none`.

Docker stores the SMB options when it creates the volume. After changing `SMB_*` in `.env`, run
`docker compose down && docker volume rm backup_smb-backup && docker compose up -d`.

## Run a backup now

```sh
docker compose exec backup sh -c 'set -a; . /etc/dockervolumebackup/conf.d/pocketid.env; backup'
```

## Restore

```sh
age -d -o pocketid.tar.gz pocketid-2026-10-25T03-00-00.tar.gz.age   # asks for the passphrase
tar -xzf pocketid.tar.gz                                             # extracts to backup/pocketid/
```

Stop the stack, replace its directory (or the contents of its named volumes for `gramps` and `paperless-ngx`) and start it again.

Immich: the live `postgres/` directory is not archived. Restore the database from the dump in
`library/backups/` as described in the [Immich docs](https://immich.app/docs/administration/backup-and-restore).

## Adding a stack

1. Mount its data into the backup container under `/backup/<stack>` in `docker-compose.yml`
   (named volumes need an `external` entry using the full volume name, e.g. `paperless-ngx_data`).
2. Copy one of the files in `conf.d/` to `conf.d/<stack>.env` and replace the name.
3. Add the label `docker-volume-backup.stop-during-backup=<stack>` to its containers that write databases.
4. `docker compose up -d --force-recreate` here.

Not covered: `windmill` (its ports conflict with traefik, so it does not seem to be deployed) and
`homebox`, `navidrome`, `trek` (no compose file in this repo).
