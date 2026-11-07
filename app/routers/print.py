import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlmodel import Session, select

from ..database import get_session
from ..label_preview import PreviewError, render_preview_png
from ..models import FoodItem, PrintLog
from ..printer import PrinterError, send_to_printer
from ..templates import templates
from ..utils import format_staff_name
from ..zpl import build_zpl

router = APIRouter()

# The kitchen's local time. The container clocks in UTC, so deriving "today"
# from the bare system clock would date any label printed after 19:00 EST as
# tomorrow. The Pi's own timezone is America/New_York; override with
# APP_TIMEZONE if the restaurant ever moves.
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/New_York")


def _local_today() -> date:
    return datetime.now(ZoneInfo(APP_TIMEZONE)).date()


def _print_dates(session: Session, food_name: str) -> tuple[date, date | None]:
    """Resolve the prep and use-by dates at print time, from the server's
    clock — never from the browser.

    The kitchen screen is left open for days at a time, so any date the page
    captured at load time (as the previous data-today attribute did) goes
    stale: a label printed a week after the page was opened would carry that
    old date. Deriving both dates here also means a cached copy of the old
    JavaScript can't reintroduce stale dates, since whatever it submits is
    ignored.
    """
    prepped = _local_today()
    item = session.exec(select(FoodItem).where(FoodItem.name == food_name.strip())).first()
    shelf_life = item.shelf_life_days if item else None
    expiration = prepped + timedelta(days=shelf_life) if shelf_life else None
    return prepped, expiration


@router.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)):
    items = session.exec(select(FoodItem).order_by(FoodItem.name)).all()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"items": items},
    )


@router.post("/print")
def print_label(
    food_name: str = Form(...),
    initials: str = Form(...),
    session: Session = Depends(get_session),
):
    staff_name = format_staff_name(initials)
    prepped, expiration = _print_dates(session, food_name)
    zpl = build_zpl(
        food_name,
        staff_name,
        prepped.isoformat(),
        expiration.isoformat() if expiration else None,
    )

    error = None
    try:
        send_to_printer(zpl)
    except PrinterError as exc:
        error = str(exc)

    log = PrintLog(
        food_name=food_name.strip(),
        initials=staff_name,
        prepped_date=prepped,
        expiration_date=expiration,
    )
    session.add(log)
    session.commit()

    return JSONResponse({"error": error})


@router.post("/print/preview")
def print_preview(
    food_name: str = Form(...),
    initials: str = Form(...),
    session: Session = Depends(get_session),
):
    """Renders the label as a PNG instead of printing it — used by Test Mode
    on the kitchen screen. Does not touch the printer or the print log."""
    staff_name = format_staff_name(initials)
    prepped, expiration = _print_dates(session, food_name)
    zpl = build_zpl(
        food_name,
        staff_name,
        prepped.isoformat(),
        expiration.isoformat() if expiration else None,
    )
    try:
        png = render_preview_png(zpl)
    except PreviewError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    return Response(content=png, media_type="image/png")
