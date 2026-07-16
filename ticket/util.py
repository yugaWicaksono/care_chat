import secrets

# no 0/O/1/I/L — avoids human misreads when a ticket id is read aloud or typed by hand
_ID_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

def generate_ticket_id(length: int = 8) -> str:
    return "".join(secrets.choice(_ID_ALPHABET) for _ in range(length))

