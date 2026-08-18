import os

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .auth import AdminAuthRequired
from .database import init_db
from .routers import admin as admin_router
from .routers import print as print_router

DATA_DIR = os.getenv("DATA_DIR", "./data")
PHOTO_DIR = os.path.join(DATA_DIR, "photos")
os.makedirs(PHOTO_DIR, exist_ok=True)

app = FastAPI(title="Burgerlove Label Printer")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"))

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/photos", StaticFiles(directory=PHOTO_DIR), name="photos")

app.include_router(print_router.router)
app.include_router(admin_router.router)


@app.exception_handler(AdminAuthRequired)
async def admin_auth_required_handler(request: Request, exc: AdminAuthRequired):
    return RedirectResponse("/admin/login", status_code=303)


@app.on_event("startup")
def on_startup():
    init_db()
