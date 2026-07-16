import os
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from ticket import get_ticket, list_tickets

BASE = Path(__file__).parent

router = APIRouter()

security = HTTPBasic()
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    if not ADMIN_PASSWORD:
        raise HTTPException(500, "ADMIN_PASSWORD not set — add it to .env")
    valid = secrets.compare_digest(credentials.username, ADMIN_USER) and secrets.compare_digest(
        credentials.password, ADMIN_PASSWORD
    )
    if not valid:
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Basic"})


@router.get("/admin/tickets")
def admin_tickets_page(_: None = Depends(require_admin)):
    return FileResponse(BASE / "static" / "tickets.html")


@router.get("/api/tickets")
def api_tickets_list(_: None = Depends(require_admin)):
    return list_tickets()


@router.get("/api/tickets/{ticket_id}")
def api_ticket_detail(ticket_id: str, _: None = Depends(require_admin)):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(404, "ticket not found")
    return ticket
