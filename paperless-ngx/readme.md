# Backup

```
mount -t cifs -o credentials=~/.credentials //192.168.178.152/apps-backup /mnt/truenas_backup
docker compose exec -T webserver document_exporter /usr/src/paperless/export --no-thumbnail --use-folder-prefix --zip
mv /mnt/data/homelab/paperless-ngx/export/export-X.zip /mnt/truenas_backup/paperless-ngx/ 
```
