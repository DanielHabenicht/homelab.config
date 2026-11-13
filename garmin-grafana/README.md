# Garmin Grafana

[garmin-grafana](https://github.com/arpanghosh8453/garmin-grafana) pulls the
health data from Garmin Connect every 5 minutes into InfluxDB: sleep (stages
and score), resting and intraday heart rate, HRV, stress, Body Battery,
breathing, steps, VO2max, race predictions, body composition and activities.
Grafana shows it as dashboards for long-term trends.

Runs at <https://garmin.home.aquiver.de>.

It only covers Garmin. Activities from Runtastic, Under Armour etc. live in
[Endurain](../endurain/README.md).

## Setup

1. `cp .env.example .env` and fill in the passwords.
2. Pocket ID: add an OIDC client `Grafana` with callback URL
   `https://garmin.home.aquiver.de/login/generic_oauth` and put its client ID
   and secret into `.env`.
3. First Garmin login (asks for email, password and the MFA code, only once):

   ```sh
   docker compose run --rm garmin-fetch-data
   ```

   The tokens end up in `garminconnect-tokens/` and stay valid for about a
   year. After that, stop the stack, empty that folder and log in again.
4. `docker compose up -d`

Grafana logs in through Pocket ID. The local `admin` account is still
reachable at `/login?disableAutoLogin=true`.

## Pulling old data

The first start only fetches the last 7 days. Older data, newest first,
5 seconds per day (so ~30 minutes per year):

```sh
docker compose run --rm -e MANUAL_START_DATE=2015-01-01 -e MANUAL_END_DATE=2026-11-13 garmin-fetch-data
```

If it stops, restart it with `MANUAL_END_DATE` set to the last day in the log.
Garmin only serves the daily values for data older than six months, intraday
details (heart rate curve, sleep stages) are gone for those days.

## Dashboards

`provisioning/dashboards/` holds the upstream dashboards (commit `8375155`,
BSD-3-Clause, see `LICENSE` there), with the datasource placeholder
`${DS_GARMIN_STATS}` replaced by `garmin_influxdb` like upstream's
`easy-install.sh` does. To update, copy the new JSON from
`Grafana_Dashboard/` in the upstream repo and run the same replacement:

```sh
sed -i 's/\${DS_GARMIN_STATS}/garmin_influxdb/g' provisioning/dashboards/Garmin-Grafana-Dashboard.json
```

Changes made in the UI are kept in Grafana's database until the file changes,
save a copy as a new dashboard to keep your own version.

## Backup

`influxdb/` and `grafana/` are copied weekly while both are stopped (see
`../backup`). `garminconnect-tokens/` is not backed up, log in again instead.
