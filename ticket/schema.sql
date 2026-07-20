CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    product TEXT NOT NULL,
    product_model TEXT,
    issue TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_info TEXT NOT NULL,
    address TEXT NOT NULL,
    notes TEXT,
    client_number TEXT,
    severity TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

-- re-running this file against an existing table (see AGENTS.md) needs this to add the column
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS product_model TEXT;
