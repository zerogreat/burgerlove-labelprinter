import csv
import io
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from PIL import Image
from sqlmodel import Session, select

from ..auth import check_credentials, require_admin
from ..database import get_session
from ..models import FoodItem, PrintLog
from ..templates import templates

router = APIRouter(prefix="/admin")

PHOTO_DIR = os.path.join(os.getenv("DATA_DIR", "./data"), "photos")
os.makedirs(PHOTO_DIR, exist_ok=True)


def save_photo(photo: UploadFile) -> str:
    image = Image.open(photo.file).convert("RGB")
    image.thumbnail((400, 400))
    filename = f"{uuid.uuid4().hex[:12]}.jpg"
    image.save(os.path.join(PHOTO_DIR, filename), "JPEG", quality=85)
    return filename


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "admin/login.html", {"error": None})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if check_credentials(username, password):
        request.session["admin"] = True
        return RedirectResponse("/admin/items", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin/login.html",
        {"error": "Invalid credentials"},
        status_code=401,
    )


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


@router.get("", include_in_schema=False)
def admin_root():
    return RedirectResponse("/admin/items", status_code=303)


@router.get("/items", response_class=HTMLResponse)
def list_items(request: Request, session: Session = Depends(get_session), _=Depends(require_admin)):
    items = session.exec(select(FoodItem).order_by(FoodItem.name)).all()
    return templates.TemplateResponse(request, "admin/items.html", {"items": items})


@router.get("/items/new", response_class=HTMLResponse)
def new_item_form(request: Request, _=Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/item_form.html", {"item": None})


@router.post("/items/new")
def create_item(
    name: str = Form(...),
    shelf_life_days: str = Form(""),
    photo: UploadFile | None = File(None),
    session: Session = Depends(get_session),
    _=Depends(require_admin),
):
    item = FoodItem(
        name=name.strip()[:32],
        shelf_life_days=int(shelf_life_days) if shelf_life_days else None,
    )
    if photo is not None and photo.filename:
        item.photo_path = save_photo(photo)
    session.add(item)
    session.commit()
    session.refresh(item)
    return RedirectResponse(f"/admin/items/{item.id}/edit", status_code=303)


@router.get("/items/{item_id}/edit", response_class=HTMLResponse)
def edit_item_form(
    item_id: int,
    request: Request,
    session: Session = Depends(get_session),
    _=Depends(require_admin),
):
    item = session.get(FoodItem, item_id)
    return templates.TemplateResponse(request, "admin/item_form.html", {"item": item})


@router.post("/items/{item_id}/edit")
def update_item(
    item_id: int,
    name: str = Form(...),
    shelf_life_days: str = Form(""),
    photo: UploadFile | None = File(None),
    session: Session = Depends(get_session),
    _=Depends(require_admin),
):
    item = session.get(FoodItem, item_id)
    item.name = name.strip()[:32]
    item.shelf_life_days = int(shelf_life_days) if shelf_life_days else None
    if photo is not None and photo.filename:
        item.photo_path = save_photo(photo)
    session.add(item)
    session.commit()
    return RedirectResponse("/admin/items", status_code=303)


@router.post("/items/{item_id}/delete")
def delete_item(item_id: int, session: Session = Depends(get_session), _=Depends(require_admin)):
    item = session.get(FoodItem, item_id)
    if item:
        session.delete(item)
        session.commit()
    return RedirectResponse("/admin/items", status_code=303)


@router.post("/items/{item_id}/photo/delete")
def delete_photo(item_id: int, session: Session = Depends(get_session), _=Depends(require_admin)):
    item = session.get(FoodItem, item_id)
    if item and item.photo_path:
        photo_file = os.path.join(PHOTO_DIR, item.photo_path)
        if os.path.exists(photo_file):
            os.remove(photo_file)
        item.photo_path = None
        session.add(item)
        session.commit()
    return {"ok": True}


@router.get("/log", response_class=HTMLResponse)
def print_log(request: Request, session: Session = Depends(get_session), _=Depends(require_admin)):
    logs = session.exec(select(PrintLog).order_by(PrintLog.printed_at.desc()).limit(200)).all()
    return templates.TemplateResponse(request, "admin/log.html", {"logs": logs})


@router.get("/export.csv")
def export_csv(session: Session = Depends(get_session), _=Depends(require_admin)):
    items = session.exec(select(FoodItem).order_by(FoodItem.name)).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["name", "shelf_life_days"])
    for item in items:
        writer.writerow([item.name, item.shelf_life_days or ""])

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=food_items.csv"},
    )
