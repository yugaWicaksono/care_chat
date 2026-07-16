import psycopg
from psycopg.rows import dict_row

from db import DATABASE_URL


def insert_ticket(ticket: dict) -> None:
    """
    Insert a ticket into the database
    :param ticket: ticket data as dict
    """
    # fresh connection per insert, no pool — same reasoning as find_customer
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tickets (ticket_id, product, issue, contact_name, contact_info, "
                "address, notes, client_number, severity, created_at) "
                "VALUES (%(ticket_id)s, %(product)s, %(issue)s, %(contact_name)s, %(contact_info)s, "
                "%(address)s, %(notes)s, %(client_number)s, %(severity)s, %(created_at)s)",
                ticket,
            )


def list_tickets() -> list[dict]:
    """
    List all tickets in the database
    """
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tickets ORDER BY created_at DESC")
            return cur.fetchall()


def get_ticket(ticket_id: str) -> dict | None:
    """
    Get a ticket by its ID
    :param ticket_id:
    """
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tickets WHERE ticket_id = %s", (ticket_id,))
            return cur.fetchone()