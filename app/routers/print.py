from datetime import date

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


@router.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)):
    items = session.exec(select(FoodItem).order_by(FoodItem.name)).all()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"items": items, "today": date.today().isoformat()},
    )


@router.post("/print")
def print_label(
    food_name: str = Form(...),
    initials: str = Form(...),
    prepped_date: str = Form(...),
    expiration_date: str = Form(""),
    session: Session = Depends(get_session),
):
    staff_name = format_staff_name(initials)
    zpl = build_zpl(food_name, staff_name, prepped_date, expiration_date or None)

    error = None
    try:
        send_to_printer(zpl)
    except PrinterError as exc:
        error = str(exc)

    log = PrintLog(
        food_name=food_name.strip(),
        initials=staff_name,
        prepped_date=date.fromisoformat(prepped_date),
        expiration_date=date.fromisoformat(expiration_date) if expiration_date else None,
    )
    session.add(log)
    session.commit()

    return JSONResponse({"error": error})


@router.post("/print/preview")
def print_preview(
    food_name: str = Form(...),
    initials: str = Form(...),
    prepped_date: str = Form(...),
    expiration_date: str = Form(""),
):
    """Renders the label as a PNG instead of printing it — used by Test Mode
    on the kitchen screen. Does not touch the printer or the print log."""
    staff_name = format_staff_name(initials)
    zpl = build_zpl(food_name, staff_name, prepped_date, expiration_date or None)
    try:
        png = render_preview_png(zpl)
    except PreviewError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    return Response(content=png, media_type="image/png")
