import sqlite3
from icecream import ic as print


# -----------------------------
# CONNECTION
# -----------------------------

def get_connection(db_name: str):

    try:
        conn = sqlite3.connect(db_name)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except Exception as e:
        print(f'Connection error: {e}')
        raise


# -----------------------------
# USERS
# -----------------------------

def create_users(connection):

    query = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        role TEXT CHECK(role IN ('admin','manager','accountant')),

        telegram_id INTEGER UNIQUE,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    with connection:
        connection.execute(query)
    print("Table users created")


# -----------------------------
# COMPANIES
# -----------------------------

def create_companies(connection):

    query = """
    CREATE TABLE IF NOT EXISTS companies (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL UNIQUE,

        country TEXT
    );
    """

    with connection:

        connection.execute(query)

        connection.executemany(
            """
            INSERT OR IGNORE INTO companies (name, country)
            VALUES (?, ?)
            """,
            [
                ("LLC Steiner Ukraine", "Kyiv"),
                ("Steiner Polska sp. z o.o.", "Warsaw"),
                ("LLC Spels", "Kyiv"),
                ("Spels MEA", "Dubai")
            ]
        )

    print("Table companies created and seeded")


# -----------------------------
# PROCESSES
# -----------------------------

def create_processes(connection):

    query = """
    CREATE TABLE IF NOT EXISTS processes (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        process_number TEXT UNIQUE,

        client_id INTEGER,

        origin_company_id INTEGER,

        description TEXT,

        start_date DATE,
        end_date DATE,

        status TEXT CHECK(status IN ('open','closed','cancelled')) DEFAULT 'open',

        steiner_poland_involved INTEGER DEFAULT 0,

        created_by INTEGER,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (client_id) REFERENCES clients(id),

        FOREIGN KEY (origin_company_id) REFERENCES companies(id),

        FOREIGN KEY (created_by) REFERENCES users(id)

    );
    """

    with connection:
        connection.execute(query)

    print("Table processes created")


# -----------------------------
# INVOICES
# -----------------------------

def create_invoices(connection):

    query = """
        CREATE TABLE IF NOT EXISTS invoices (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            invoice_number TEXT,

            process_id INTEGER NOT NULL,

            seller_company_id INTEGER,

            buyer_company_id INTEGER,

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

            FOREIGN KEY (process_id) REFERENCES processes(id),

            FOREIGN KEY (seller_company_id) REFERENCES companies(id),

            FOREIGN KEY (buyer_company_id) REFERENCES companies(id)

        );
    """

    with connection:
        connection.execute(query)

    print("Table invoices created")


# -----------------------------
# PAYMENTS
# -----------------------------

def create_payments(connection):

    query = """
    CREATE TABLE IF NOT EXISTS payments (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        payment_number TEXT,

        process_id INTEGER,

        invoice_id INTEGER,

        from_company_id INTEGER,

        to_company_id INTEGER,

        amount NUMERIC,

        currency CHAR(3),

        payment_date DATE,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (process_id) REFERENCES processes(id),

        FOREIGN KEY (invoice_id) REFERENCES invoices(id),

        FOREIGN KEY (from_company_id) REFERENCES companies(id),

        FOREIGN KEY (to_company_id) REFERENCES companies(id)
    );
    """

    with connection:
        connection.execute(query)

    print("Table payments created")


# -----------------------------
# EVENTS (AUDIT LOG)
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

        FOREIGN KEY (process_id) REFERENCES processes(id),

        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """

    with connection:
        connection.execute(query)

    print("Table events created")


# -----------------------------
# SUPPLIERS
# -----------------------------

def create_suppliers(connection):

    query = """
    CREATE TABLE IF NOT EXISTS suppliers (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        process_id INTEGER,

        supplier_name TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (process_id) REFERENCES processes(id)
    );
    """

    with connection:
        connection.execute(query)

    print("Table suppliers created")


# -----------------------------
# INDEXES
# -----------------------------

def create_indexes(connection):

    queries = [

        "CREATE INDEX IF NOT EXISTS idx_process_number ON processes(process_number)",

        "CREATE INDEX IF NOT EXISTS idx_process_client ON processes(client_id)",

        "CREATE INDEX IF NOT EXISTS idx_invoice_process ON invoices(process_id)",

        "CREATE INDEX IF NOT EXISTS idx_payment_process ON payments(process_id)",

        "CREATE INDEX IF NOT EXISTS idx_payment_invoice ON payments(invoice_id)",

        "CREATE INDEX IF NOT EXISTS idx_events_process ON events(process_id)"

        
    ]

    with connection:

        for query in queries:
            connection.execute(query)

    print("Indexes created")

#------------------------------
#CLIENTS
#------------------------------

def create_clients(connection):

    query = """
    CREATE TABLE IF NOT EXISTS clients (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL UNIQUE,ʼ

    );
    """

    with connection:
        connection.execute(query)
    print('Table clients created')
# -----------------------------
# MAIN
# -----------------------------

def main():

    connection = get_connection("DATABASE.db")

    try:

        create_users(connection)

        create_companies(connection)

        create_processes(connection)

        create_invoices(connection)

        create_payments(connection)

        create_events(connection)

        create_suppliers(connection)

        create_indexes(connection)

        create_clients(connection)

    finally:

        connection.close()

        print("Connection closed")


if __name__ == "__main__":

    main()