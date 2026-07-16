import secrets

# no 0/O/1/I/L — avoids human misreads when a ticket id is read aloud or typed by hand
_ID_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

def generate_ticket_id(length: int = 8) -> str:
    # ponytail: 31**8 ~= 8.5e11 combinations, plenty at this app's ticket volume;
    # add a collision retry loop only if that stops being true
    return "".join(secrets.choice(_ID_ALPHABET) for _ in range(length))

