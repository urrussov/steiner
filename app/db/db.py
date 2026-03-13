import sqlite3
from icecream import ic


# -----------------------------
# CONNECTION
# -----------------------------

def get_connection(db_name: str):

    try:
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    except Exception as e:

        ic(f"Connection error: {e}")
        raise


# -----------------------------
# USERS
# -----------------------------

def create_users(connection):

    query = """
    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        role TEXT CHECK(role IN (
            'admin',
            'manager',
            'accountant'
        )),

        telegram_id INTEGER UNIQUE,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    with connection:
        connection.execute(query)

    ic("Table users created")


# -----------------------------
# ENTITIES
# -----------------------------

def create_entities(connection):

    query = """
    CREATE TABLE IF NOT EXISTS entities (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL UNIQUE,

        type TEXT CHECK(type IN (
            'company',
            'client',
            'supplier'
        )),

        country TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    with connection:

        connection.execute(query)

        connection.executemany(
            """
            INSERT OR IGNORE INTO entities(name,type,country)
            VALUES(?,?,?)
            """,
            [
                ("LLC Steiner Ukraine","company","Ukraine"),
                ("Steiner Polska sp. z o.o.","company","Poland"),
                ("LLC Spels","company","Ukraine"),
                ("Spels MEA","company","UAE")
            ]
        )

    ic("Table entities created")


# -----------------------------
# PROCESSES
# -----------------------------

def create_processes(connection):

    query = """
    CREATE TABLE IF NOT EXISTS processes (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        process_number TEXT UNIQUE NOT NULL,

        client_entity_id INTEGER NOT NULL,

        managing_company_id INTEGER NOT NULL,

        description TEXT,

        start_date DATE,

        end_date DATE,

        status TEXT CHECK(status IN (
            'open',
            'closed',
            'cancelled'
        )) DEFAULT 'open',

        steiner_poland_involved INTEGER DEFAULT 0,

        created_by INTEGER,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(client_entity_id) REFERENCES entities(id),

        FOREIGN KEY(managing_company_id) REFERENCES entities(id),

        FOREIGN KEY(created_by) REFERENCES users(id)

    );
    """

    with connection:
        connection.execute(query)

    ic("Table processes created")


# -----------------------------
# PROCESS PARTICIPANTS
# -----------------------------

def create_process_participants(connection):

    query = """
    CREATE TABLE IF NOT EXISTS process_participants (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        process_id INTEGER NOT NULL,

        entity_id INTEGER NOT NULL,

        role TEXT CHECK(role IN (
            'client',
            'supplier',
            'company'
        )),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(process_id) REFERENCES processes(id),

        FOREIGN KEY(entity_id) REFERENCES entities(id),

        UNIQUE(process_id, entity_id)
    );
    """

    with connection:
        connection.execute(query)

    ic("Table process_participants created")


# -----------------------------
# INVOICES
# -----------------------------

def create_invoices(connection):

    query = """
    CREATE TABLE IF NOT EXISTS invoices (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        invoice_number TEXT,

        process_id INTEGER NOT NULL,

        seller_entity_id INTEGER NOT NULL,

        buyer_entity_id INTEGER NOT NULL,

        invoice_type TEXT CHECK(invoice_type IN (
            'proforma',
            'final'
        )),

        invoice_date DATE,

        amount NUMERIC,

        currency CHAR(3),

        exchange_rate_to_eur NUMERIC,

        amount_eur NUMERIC,

        status TEXT CHECK(status IN (
            'issued',
            'partially_paid',
            'paid',
            'cancelled'
        )) DEFAULT 'issued',

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(invoice_number,process_id),

        FOREIGN KEY(process_id) REFERENCES processes(id),

        FOREIGN KEY(seller_entity_id) REFERENCES entities(id),

        FOREIGN KEY(buyer_entity_id) REFERENCES entities(id)

    );
    """

    with connection:
        connection.execute(query)

    ic("Table invoices created")


# -----------------------------
# PAYMENTS
# -----------------------------

def create_payments(connection):

    query = """
    CREATE TABLE IF NOT EXISTS payments (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        payment_number TEXT,

        process_id INTEGER NOT NULL,

        invoice_id INTEGER,

        from_entity_id INTEGER NOT NULL,

        to_entity_id INTEGER NOT NULL,

        amount NUMERIC,

        currency CHAR(3),

        exchange_rate_to_eur NUMERIC,

        payment_date DATE,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(process_id) REFERENCES processes(id),

        FOREIGN KEY(invoice_id) REFERENCES invoices(id),

        FOREIGN KEY(from_entity_id) REFERENCES entities(id),

        FOREIGN KEY(to_entity_id) REFERENCES entities(id)

    );
    """

    with connection:

        connection.execute(query)

    ic("Table payments created")


# -----------------------------
# LEDGER
# -----------------------------

def create_ledger(connection):

    query = """
    CREATE TABLE IF NOT EXISTS ledger (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        process_id INTEGER NOT NULL,

        entity_from_id INTEGER NOT NULL,

        entity_to_id INTEGER NOT NULL,

        amount_eur NUMERIC NOT NULL,

        entry_type TEXT CHECK(entry_type IN (
            'invoice',
            'payment',
            'internal_transfer'
        )),

        reference_id INTEGER,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(process_id) REFERENCES processes(id),

        FOREIGN KEY(entity_from_id) REFERENCES entities(id),

        FOREIGN KEY(entity_to_id) REFERENCES entities(id)

    );
    """

    with connection:
        connection.execute(query)

    ic("Table ledger created")


# -----------------------------
# PROCESS BALANCE
# -----------------------------

def create_process_balance(connection):

    query = """
    CREATE TABLE IF NOT EXISTS process_balance (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        process_id INTEGER NOT NULL,

        from_entity_id INTEGER NOT NULL,

        to_entity_id INTEGER NOT NULL,

        amount_eur NUMERIC,

        balance_type TEXT CHECK(balance_type IN (
            'client_payment',
            'supplier_cost',
            'internal_transfer'
        )),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(process_id) REFERENCES processes(id),

        FOREIGN KEY(from_entity_id) REFERENCES entities(id),

        FOREIGN KEY(to_entity_id) REFERENCES entities(id)

    );
    """

    with connection:
        connection.execute(query)

    ic("Table process_balance created")


# -----------------------------
# EVENTS
# -----------------------------

def create_events(connection):

    query = """
    CREATE TABLE IF NOT EXISTS events (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        process_id INTEGER,

        user_id INTEGER,

        event_type TEXT,

        description TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(process_id) REFERENCES processes(id),

        FOREIGN KEY(user_id) REFERENCES users(id)

    );
    """

    with connection:
        connection.execute(query)

    ic("Table events created")


# -----------------------------
# INDEXES
# -----------------------------

def create_indexes(connection):

    queries = [

        "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)",

        "CREATE INDEX IF NOT EXISTS idx_process_number ON processes(process_number)",

        "CREATE INDEX IF NOT EXISTS idx_invoice_process ON invoices(process_id)",

        "CREATE INDEX IF NOT EXISTS idx_payment_process ON payments(process_id)",

        "CREATE INDEX IF NOT EXISTS idx_payment_invoice ON payments(invoice_id)",

        "CREATE INDEX IF NOT EXISTS idx_events_process ON events(process_id)",

        "CREATE INDEX IF NOT EXISTS idx_ledger_process ON ledger(process_id)",

        "CREATE INDEX IF NOT EXISTS idx_ledger_from ON ledger(entity_from_id)",

        "CREATE INDEX IF NOT EXISTS idx_ledger_to ON ledger(entity_to_id)",

        "CREATE INDEX IF NOT EXISTS idx_participants_process ON process_participants(process_id)",

        "CREATE INDEX IF NOT EXISTS idx_participants_entity ON process_participants(entity_id)"

    ]

    with connection:

        for query in queries:
            connection.execute(query)

    ic("Indexes created")


# -----------------------------
# MAIN
# -----------------------------

def main():

    connection = get_connection("DATABASE.db")

    try:

        create_users(connection)

        create_entities(connection)

        create_processes(connection)

        create_process_participants(connection)

        create_invoices(connection)

        create_payments(connection)

        create_ledger(connection)

        create_process_balance(connection)

        create_events(connection)

        create_indexes(connection)

    finally:

        connection.close()

        ic("Connection closed")


if __name__ == "__main__":

    main()