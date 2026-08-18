# Burgerlove Label Printer — Plan

Locally hosted prep-label printing for the kitchen. A tablet or phone on the
restaurant wifi hits a small web app running on a Raspberry Pi 4; staff pick a
prepped item, confirm initials/dates, and print a 1"x1" thermal label
directly to a network-attached Zebra ZD411 over raw ZPL.

## Hardware

- **Printer**: Zebra ZD411, **300 dpi**, ethernet — plugged straight into the
  network switch, DHCP reservation for a fixed IP. Raw ZPL sent over TCP port
  9100, no drivers/spooler. (Originally assumed 203 dpi; corrected after
  reading the printer's own config printout — `RESOLUTION` showed 12 dots/mm
  and the self-calibrated `LABEL LENGTH` was ~315 dots, both only consistent
  with 300 dpi. See `app/zpl.py`.)
- **Labels**: dissolvable direct-thermal, 1"x1".
- **Interface**: wall-mounted Android tablet (or any phone on the same wifi),
  browser pointed at the Pi, "Add to Home Screen" for an app-like feel. No
  login required for the main print screen — trust the wifi network.

## Architecture

```
[Zebra ZD411] --ethernet--> [switch] <--wifi-- [tablet / phones]
      ^ raw ZPL, port 9100          |
      |                             v
      +-------------------- [Raspberry Pi 4]
                             FastAPI app (Docker)
                             SQLite (food_items, print_log)
                             /data/photos/*.jpg
```

Single Pi, single Docker container, single SQLite file. No message queue, no
separate DB server, no JS build step, no CDN dependency — everything the
kitchen-facing pages need ships from the Pi itself so it keeps working with
zero internet access.

## Software stack

- **Backend**: FastAPI + Uvicorn, SQLModel over SQLite.
- **Frontend**: server-rendered Jinja2 templates + small hand-written vanilla
  JS (no Alpine/HTMX/React). The interactions needed (tap an item, compute an
  expiration date, POST a print request, show a toast) don't earn a
  framework, and a framework would mean either a build step or a CDN
  dependency — both against the "extremely lightweight, works offline"
  goal.
- **Auth**: single shared admin password (`ADMIN_USERNAME`/`ADMIN_PASSWORD`
  in `.env`), compared with `secrets.compare_digest`, session via a signed
  cookie (`starlette.middleware.sessions`). No bcrypt/user table needed for
  one shared credential on a trusted LAN appliance.
- **Packaging**: one Docker image, `docker-compose.yml` with one service,
  `./data` bind-mounted for the SQLite file + `photos/`.

## Data model

```
food_items
  id, name, shelf_life_days (nullable), photo_path (nullable)

print_log        -- audit trail, viewable under /admin/log
  id, food_name, initials, prepped_date, expiration_date, printed_at
```

Item picker and admin list are always sorted alphabetically by name — no
manual ordering field.

## Main print screen — flow

1. Fields: **Initials** (required, remembered per-device in `localStorage`
   for speed, still editable), **Prepped date** (defaults to today, editable
   date picker), **Item** (editable text, populated by tapping a grid
   button).
2. Tapping an item button fills the item field and, if that item has a
   `shelf_life_days`, auto-calculates and fills **Expiration date** from the
   prepped date. No shelf life defined -> expiration stays blank. Both dates
   and the item name can be overwritten by hand.
3. **Big green PRINT button**, always enabled. Every tap fires an
   independent `/print` request — no "already printed" guard, no
   confirmation dialog. Tap it 3 times, get 3 labels. A small toast shows a
   running "Printed x3" count that resets after ~2.5s of inactivity.
4. If the printer can't be reached, the tap fails with a visible error
   instead of silently doing nothing — important since there's no print
   spooler to check later.

## Label design (ZPL, 300 dpi, 1"x1" = 300x300 dots)

See `app/zpl.py` for the current field layout (source of truth — this file
gets tuned often, don't treat the snippet below as authoritative). As of
this writing: food name up top (up to 2 lines), a "Prepped by:" caption with
the initials rendered much larger next to it, the prepped date below that,
then EXP as a small caption over a large centered date at the bottom — EXP
still gets the most visual weight since it's the food-safety-critical field.
Dates are formatted `D-Mon-YY` (e.g. `3-Jan-26`).

`LABEL_TOP_OFFSET` in `app/zpl.py` (emitted as ZPL `^LT`) is a software nudge
for print registration drift, tunable without touching field positions.

Physical tuning happened against the real printer — a 1"x1" label is tight,
and no ZPL simulator perfectly matches real output, though the app's
built-in Test Mode (Labelary-rendered preview, see `/print/preview`) gets
close enough to dial in layout/wrapping before burning physical labels.

## Admin panel (`/admin`, single shared login)

- CRUD for food items (name, shelf life in days). No soft-delete/active
  toggle — an item either exists and shows on the picker, or it's deleted
  for good. List sorted
  alphabetically.
- **Print log** view — read-only audit trail (who printed what, when).
- **CSV export** (`/admin/export.csv`) — generated on the fly from current
  `food_items` on click. No cron, no scheduler, no nightly job: since it's
  only ever pulled via an explicit click, there's nothing to gain from
  precomputing it, and it's always current this way.
- **Photo capture + crop**: `<input type="file" capture="environment">` to
  grab a photo from the device camera, then a small hand-rolled canvas
  cropper (drag a fixed square crop box over the image, no external
  library) before uploading. The cropped image is resized/compressed
  server-side (Pillow, 400x400 JPEG) and saved to `/data/photos/`.
  **This photo is for the web UI's tap buttons only** — at 1"x1" thermal
  resolution a photo on the printed label itself would be unusable, so it's
  intentionally left off the label.

## Deployment (Raspberry Pi 4, eventual target)

- Raspberry Pi OS Lite (64-bit) + Docker + docker-compose.
- `avahi-daemon` so the app is reachable at `http://labelprinter.local:8000`
  instead of a raw IP.
- DHCP reservations for both the Pi and the printer.
- `./data` bind-mounted outside the container so image rebuilds never touch
  the DB or photos.
- No photo backup needed (per decision) — only the DB itself is worth
  protecting, and it's a single file that's trivial to copy if ever wanted.

## Local preview (this repo, right now)

See [README.md](README.md) for exact steps. Short version: `docker compose
up --build`, open `http://localhost:8000`. `PRINTER_IP` won't resolve to a
real printer yet — print attempts will fail with a visible error, which is
expected until the ZD411 is on the network. Everything else (item picker,
admin CRUD, photo crop, CSV export, print log) is fully testable now.

## Open items for when the printer arrives

- Tune label font sizes/positions against real hardware.
- Confirm the `PRINTER_IP` DHCP reservation.
- Decide `SECRET_KEY` / `ADMIN_PASSWORD` for the real deployment (the
  checked-in `.env` values are dev-only placeholders).
