# Burgerlove Label Printer

See [PLAN.md](PLAN.md) for the full architecture writeup. This is the
quickstart.

## Run it locally (Docker Desktop, Windows)

```
docker compose up --build
```

Then open http://localhost:8000

- Kitchen print screen: `/`
- Admin panel: `/admin/items` (login: `admin` / `changeme`, from `.env`)

The printer isn't on the network yet, so tapping PRINT will show a "could
not reach printer" toast — that's expected. Everything else (item picker,
expiration auto-calc, admin CRUD, photo capture + crop, print log, CSV
export) works fully without the printer.

## Project layout

```
app/
  main.py           FastAPI app, mounts routers + static/photos
  database.py       SQLite engine/session
  models.py         FoodItem, PrintLog (SQLModel)
  zpl.py            builds the ZPL string for a label
  printer.py        raw socket send to PRINTER_IP:9100
  auth.py           shared admin credential check + session guard
  templates.py      shared Jinja2Templates instance
  routers/
    print.py        "/" kitchen screen, "/print"
    admin.py        "/admin/*" — login, item CRUD, photo upload, log, CSV
  templates/         Jinja2 templates
  static/            hand-written CSS/JS (no CDN dependencies)
data/                 sqlite db + uploaded photos (bind-mounted, gitignored)
```

## Configuration

Copy `.env.example` to `.env` (already done for local dev) and adjust:

- `PRINTER_IP` / `PRINTER_PORT` — the ZD411's network address, port 9100.
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` — shared admin login.
- `SECRET_KEY` — session cookie signing key; change before deploying
  anywhere but your own machine.

## Next steps

- Once the ZD411 is on the network, set `PRINTER_IP` and test a real print —
  the label layout in `app/zpl.py` will likely need font-size tuning against
  physical output (see PLAN.md).
- For the eventual Raspberry Pi deployment: same `docker compose up`, plus
  `avahi-daemon` for a `.local` hostname and DHCP reservations for the Pi
  and printer.
