CREATE TABLE IF NOT EXISTS customers (
    client_number TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    contact_info TEXT,
    address TEXT
);

CREATE INDEX IF NOT EXISTS idx_customers_name ON customers (lower(name));
