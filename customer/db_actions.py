import psycopg
from psycopg.rows import dict_row

from db import DATABASE_URL

def find_customer(name: str | None = None, client_number: str | None = None) -> list[dict]:
    """
    Find customer based on the client number or name
    """
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            if client_number:
                cur.execute(
                    "SELECT client_number, name, contact_info, address FROM customers "
                    "WHERE lower(client_number) = lower(%s)",
                    (client_number,),
                )
            elif name:
                cur.execute(
                    "SELECT client_number, name, contact_info, address FROM customers "
                    "WHERE name ILIKE %s",
                    (f"%{name}%",),
                )
            else:
                return []
            return cur.fetchall()

