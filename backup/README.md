# Backup

Automated backups of all stacks with [offen/docker-volume-backup](https://offen.github.io/docker-volume-backup/),
written to an SMB share and encrypted with [age](https://age-encryption.org/).

- Every file in `conf.d/` is one backup job (one archive per stack, e.g. `pocketid-2026-10-25T03-00-00.tar.gz.age`).
- Daily at 03:00 (`Europe/Berlin`), archives older than 14 days are deleted. Immich runs weekly and keeps 28 days.
- Jobs with the same schedule run one after another.
- Only application data is mounted into the backup container (data folders, dumps, named volumes).
  Config files and secrets are **not** backed up: `.env` files, `traefik/acme.json`, `git-backup/token.txt`,
  `homepage/config/services.yaml`, `super-productivity/webdav.yaml`, paperless `keys/` and `pdf-edit-config/`,
  mailarchiva `data/etc/` and `emailproxy.config`, the gramps secret volume. Keep what you need for a restore
  (e.g. Monica's `APP_KEY`, the MailArchiva encryption password) somewhere else.

## How each app is backed up

Where an app has its own backup or export, that is used. Otherwise the containers labeled
`docker-volume-backup.stop-during-backup=<stack>` are stopped while their files are copied.

| Stack | Method | Restore |
| --- | --- | --- |
| immich | Immich's automatic database dumps (`library/backups`, daily 02:00, 14 kept) + `library` without thumbnails/transcodes. Runs while Immich is running. | Restore the dump as described in the [Immich docs](https://immich.app/docs/administration/backup-and-restore), then rerun the thumbnail and transcode jobs. |
| paperless-ngx | [`document_exporter`](https://docs.paperless-ngx.com/administration/#exporter) into `export/` right before the archive (`archive-pre` label). Runs while Paperless is running. | `document_importer ../export` on the **same Paperless version**. API tokens are not exported. |
| tandoor-recipes | `pg_dumpall` into `db-dump/tandoor.sql` as in the [Tandoor docs](https://docs.tandoor.dev/system/backup/) + `mediafiles/`. | Pipe `tandoor.sql` into `psql` in a fresh db container. |
| monica | `mariadb-dump` into `db-dump/monica.sql` + `data/` (uploads). | Pipe `monica.sql` into `mariadb` in a fresh db container. |
| ubiquiti | Only the controller's own autobackups (`.unf` files). Enable them under *Settings → System → Backups* (e.g. daily). | Choose *Restore from backup* in the setup wizard of a fresh controller. |
| mailarchiva | Copies `data/` (without logs) while running, which [MailArchiva supports](https://help.mailarchiva.com/enterprise-backup) for the volume store. | Copy back, or use *Import Volume*. Needs the same encryption password, which is **not** in the backup. |
| actual-budget, bonds, gramps, n8n, pocketid, trilium | SQLite databases, no usable backup command (see below): stopped for a few seconds and copied. | Copy the files back. |
| super-productivity | WebDAV server stopped and its files copied. | Copy the files back. |
| git-backup | The mirrored repositories, copied while running. | Copy the files back. |

Considered but not used:

- **Actual Budget**: only has a per-budget export in the UI, nothing for the server.
- **Bonds**: has scheduled backups (Admin UI, written to `bonds-data/backups`). They are covered as well, but copying the stopped database is more current.
- **Gramps Web**: Gramps XML export only exists in the UI, there is no command for it.
- **n8n**: `n8n export:workflow` / `export:credentials` only cover workflows and credentials, `export:entities` is meant for migrations.
- **Pocket ID**: `pocket-id export` creates a full archive, but the docs mark it as experimental.
- **Trilium**: keeps one daily, weekly and monthly copy in `trilium-data/backup`. They are archived too, but are up to a day old.

## Setup

1. Install the CIFS tools on the Docker host: `sudo apt install cifs-utils`
2. `cp .env.example .env` and fill in the share and the age passphrase.
   Use the IP address of the NAS for `SMB_HOST`. Store the passphrase outside the homelab, without it the backups are useless.
3. Recreate the stacks so the new labels and mounts are applied (`docker compose up -d` in every changed stack directory).
4. Enable the UniFi autobackups (see table).
5. `docker compose up -d` in this directory.

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

Clone this repo, copy the extracted files into the stack directory (or into the named volumes for `gramps`; a new Flask secret is generated on start)
and continue with the app-specific step from the table above.

## Adding a stack

1. Mount only its data folders into the backup container under `/backup/<stack>/` in `docker-compose.yml`
   (named volumes need an `external` entry using the full volume name, e.g. `gramps_gramps_db`).
2. Copy one of the files in `conf.d/` to `conf.d/<stack>.env` and replace the name. Every file needs its own `EXEC_LABEL`,
   otherwise it would run the dump commands of all stacks.
3. If the app has a dump/export command, add `docker-volume-backup.exec-label=<stack>` and
   `docker-volume-backup.archive-pre=<command>` to that container. Otherwise add
   `docker-volume-backup.stop-during-backup=<stack>` to its containers that write databases.
4. `docker compose up -d --force-recreate` here.

Not covered: `windmill` (its ports conflict with traefik, so it does not seem to be deployed) and
`homebox`, `navidrome`, `trek` (no compose file in this repo).
