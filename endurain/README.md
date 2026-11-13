# Endurain

[Endurain](https://github.com/endurain-project/endurain) is a self-hosted
fitness tracker (think Strava without the cloud): activities with maps, heart
rate and pace charts, week/month/year statistics, gear tracking, goals, and
weight, steps and sleep from Garmin Connect.

Runs at <https://fitness.home.aquiver.de>.

## Setup

1. `cp .env.example .env` and fill in the secrets.
2. `docker compose up -d`
3. Log in with `admin` / `admin` and change the password right away.
4. Pocket ID: add an OIDC client
   - Callback URL: `https://fitness.home.aquiver.de/api/v1/public/idp/callback/pocket-id`
   - In Endurain: *Settings → Identity Providers → Add → Pocket ID*, slug
     `pocket-id`, issuer `https://auth.home.aquiver.de` (no trailing slash),
     scopes `openid profile email`.
   - Give the Endurain admin account the same email as in Pocket ID, otherwise
     SSO creates a second user.
   - Optional, once SSO works: *Settings → Server Settings*, turn off local
     login and turn on *Auto-redirect to SSO* (`/?forceLocalLogin=true` still
     shows the local form).
5. Garmin Connect: *Settings → Integrations → Garmin Connect*, log in (MFA is
   supported). Endurain only keeps the tokens, encrypted with `FERNET_KEY`.
   New activities are pulled every hour, body composition every four hours.

Endurain stays always on (no Sablier), the Garmin sync runs in the background.

## Importing old data

Bulk import: *Settings → Import*. Either upload a ZIP (max. 500 MiB) or copy
the files to `data/activity_files/bulk_import/<your user id>/` and start the
import from the page. `.fit`, `.tcx`, `.gpx` and `.gz` are read, everything
else is ignored, subfolders are fine. Duplicates are detected, so running an
import twice is safe, but there is **no undo**: test with a few files first.

Prefer `.fit` over `.gpx` where you have both, `.gpx` loses heart rate,
cadence and the sport type.

### Garmin history

The hourly sync only looks at the last 24 hours. For older activities either
use *Retrieve activities* in the Garmin settings with a date range, or request
the full Garmin export (*Garmin account → Data Management → Export your data*)
and bulk import the `.fit` files from
`DI_CONNECT/DI-Connect-Uploaded-Files/`.

### Runtastic / adidas Running

The export (adidas Running app → *Settings → Account → Export data*) has the
sessions as JSON in `Sport-sessions/` and the GPS tracks as `.gpx` in
`Sport-sessions/GPS-data/`. The `.gpx` files can be imported as they are, but
sessions without GPS (treadmill, gym) and the sport type, heart rate and notes
only exist in the JSON. Those need converting to `.tcx`/`.fit` first.

### Under Armour (MapMyRun / UA Record)

The account export is a CSV with one row per workout, without tracks.
Tracks can be downloaded per workout as `.tcx`/`.gpx` from the MapMyFitness
website and then imported.
