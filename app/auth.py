import os
import secrets

from fastapi import Request

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")


class AdminAuthRequired(Exception):
    pass


def check_credentials(username: str, password: str) -> bool:
    return secrets.compare_digest(username, ADMIN_USERNAME) and secrets.compare_digest(
        password, ADMIN_PASSWORD
    )


def require_admin(request: Request) -> None:
    if not request.session.get("admin"):
        raise AdminAuthRequired()
