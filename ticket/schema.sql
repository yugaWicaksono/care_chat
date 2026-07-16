CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    product TEXT NOT NULL,
    issue TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_info TEXT NOT NULL,
    address TEXT NOT NULL,
    notes TEXT,
    client_number TEXT,
    severity TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
