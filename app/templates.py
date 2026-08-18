import os

from fastapi.templating import Jinja2Templates

from .utils import item_initials

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["initials"] = item_initials


def static_version(filename: str) -> int:
    """File mtime as a cache-busting query param, so a rebuild always
    invalidates browser caches for app.css/print.js without needing to
    remember to bump a manual version number."""
    try:
        return int(os.path.getmtime(os.path.join("app", "static", filename)))
    except OSError:
        return 0


templates.env.globals["static_version"] = static_version
