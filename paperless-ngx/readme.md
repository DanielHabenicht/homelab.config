# Paperless-ngx

## Setup

```
cd keys/host
# Public Key for SSH Login
ssh-keygen -t ed25519 -f ssh_host_ed25519_key < /dev/null
ssh-keygen -t rsa -b 4096 -f ssh_host_rsa_key < /dev/null
```

## Backup

```
mount -t cifs -o credentials=~/.credentials //192.168.178.152/apps-backup /mnt/truenas_backup
docker compose exec -T webserver document_exporter /usr/src/paperless/export --no-thumbnail --use-folder-prefix --zip
mv /mnt/data/homelab/paperless-ngx/export/export-X.zip /mnt/truenas_backup/paperless-ngx/
```
