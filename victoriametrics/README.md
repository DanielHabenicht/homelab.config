# VictoriaMetrics

Long-term storage for the Home Assistant history, replacing the (discontinued) InfluxDB v1 add-on,
which bloats every Home Assistant backup.

VictoriaMetrics speaks the InfluxDB line protocol, so Home Assistant keeps using its normal
[InfluxDB integration](https://www.home-assistant.io/integrations/influxdb/), just pointed here.
Web UI (vmui): `https://metrics.home.aquiver.de/vmui/` (basic auth from `.env`).
For Grafana, add it as a *Prometheus* data source with the URL `https://metrics.home.aquiver.de`.

## Setup

```sh
cp .env.example .env    # set VM_USERNAME / VM_PASSWORD
docker compose up -d
```

`-retentionPeriod=100y` is important: the default is 1 month and VictoriaMetrics would drop
the migrated history right away.

## Migration from the InfluxDB add-on

Order: first send new data here, then copy the history. That way nothing is missing and nothing is imported twice.

### 1. Point Home Assistant to VictoriaMetrics

Change the `influxdb:` block in Home Assistant's `configuration.yaml`. Keep everything else
(`include`/`exclude`, `tags`, measurement settings) as it is, so new series get the same names as the migrated ones.

```yaml
influxdb:
  api_version: 1
  host: metrics.home.aquiver.de
  port: 443
  ssl: true
  verify_ssl: true
  database: homeassistant        # becomes the label db="homeassistant", same as in the import
  username: !secret victoriametrics_username
  password: !secret victoriametrics_password
  max_retries: 3                 # covers the few seconds VictoriaMetrics is stopped for the weekly backup
  # include/exclude/tags: unchanged
```

Restart Home Assistant. After a few minutes `{db="homeassistant"}` in vmui should show data.
Only Home Assistant's InfluxDB *sensor* platform (InfluxQL queries) does not work against VictoriaMetrics.

### 2. Copy the history with vmctl

The InfluxDB add-on must be reachable from the Docker host. In the add-on's *Configuration → Network*
make sure port `8086` is set. Use the InfluxDB user Home Assistant writes with (or create one with read access
in the add-on's Chronograf UI) and fill in `INFLUX_*` in `.env`. Then:

```sh
docker compose run --rm vmctl
```

vmctl lists the found series and asks for confirmation, then imports everything with a progress bar.
For ~3 GB expect somewhere between 30 minutes and a few hours (depends mostly on the Home Assistant hardware).
It only copies the `homeassistant` database (retention policy `autogen`), Proxmox follows in step 3.
If it gets interrupted, just run it again: the same samples are deduplicated.

Naming in VictoriaMetrics: `<measurement>_<field>` with the InfluxDB tags as labels, e.g.
Home Assistant's `°C` measurement with field `value` becomes `{__name__="°C_value", entity_id="living_room_temperature", domain="sensor", db="homeassistant"}`.
Live writes from Home Assistant use the same naming, so old and new data are one continuous series.

Only numbers are stored. Text states and the `*_str` attribute fields are skipped (on/off etc. are already
written as 0/1 by Home Assistant).

### 3. Proxmox VE

The add-on also has a `proxmox` database (Proxmox *Datacenter → Metric Server*). Proxmox' HTTP mode
authenticates with a token, which VictoriaMetrics does not support, so it writes over UDP instead
(port `8089/udp` on the Docker host, LAN only, no auth).

1. In Proxmox: *Datacenter → Metric Server*, edit the InfluxDB entry (or remove it and add a new one):
   protocol `UDP`, server = IP of the Docker host, port `8089`.
2. Copy the history: `docker compose run --rm vmctl-proxmox`

These series have no `db` label (UDP has no database name), the import skips it as well.
Grafana dashboards for Proxmox that use InfluxQL have to be rebuilt with PromQL/MetricsQL.

### 4. Check and remove the add-on

1. Compare a few sensors in vmui with the add-on (e.g. the oldest data point and a sum over a year).
2. Optionally keep one last Home Assistant backup that contains the add-on.
3. Uninstall the InfluxDB add-on (and Chronograf/Grafana dashboards using it). Home Assistant backups shrink by those ~3 GB.

## Backup

Included in the weekly backup (`backup/conf.d/victoriametrics.env`): the container is stopped for a few seconds
and `data/` is copied. VictoriaMetrics compresses much better than InfluxDB, so the archive is usually a fraction of the 3 GB.

## Tips

- Home Assistant only writes on state changes. If graphs show gaps for sensors that rarely change, add
  `-search.maxStalenessInterval=1h` (or larger) to the `command` in `docker-compose.yml`.
