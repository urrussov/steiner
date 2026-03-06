import sqlite3
from icecream import ic as print

def get_connection(db_name):
    try:
        conn = sqlite3.connect(db_name)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except Exception as e:
        print(f'Error: {e}')
        raise

def create_users(connection):
    query = """
    CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin','manager','accountant')),
    telegram_id INTEGER UNIQUE
    )
    """
    try:
        with connection:
            connection.execute(query)
        print('Table users was created')
    except Exception as e:
        print(f'Error: {e}')
        raise

def create_companies(connection):
    query = """
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        country TEXT
    )
    """

    try:
        with connection:
            connection.execute(query)

            connection.executemany(
                """
                INSERT OR IGNORE INTO companies (name, country)
                VALUES (?, ?)
                """,
                [
                    ("LLC Steiner Ukraine", "Київ"),
                    ("Steiner Polska sp. z o.o.", "Варшава"),
                    ("LLC Spels", "Київ"),
                    ("Spels MEA", "Дубай")
                ]
            )

        print("Table companies was created and seeded")

    except Exception as e:
        print(f'Error: {e}')
        raise

def create_processes(connection):
    query = """
        CREATE TABLE IF NOT EXISTS processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            process_number TEXT UNIQUE,

            client_name TEXT,

            origin_company_id INTEGER,

            description TEXT,

            start_date DATE,
            end_date DATE,

            status TEXT CHECK(status IN ('open','closed','cancelled')),
            steiner_poland_involved INTEGER DEFAULT 0,
            created_by INTEGER,

            FOREIGN KEY (origin_company_id) REFERENCES companies(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );
    """

    try:
        with connection:
            connection.execute(query)
        print('Table processes was created')

    except Exception as e:
        print(f'Error: {e}')
        raise

def create_invoices(connection):
    query = """
    CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT,
    process_id INTEGER,
    seller_company_id INTEGER,
    buyer_company_id INTEGER,
    amount NUMERIC,
    currency CHAR(3),
    invoice_type TEXT,
    status TEXT CHECK(status IN ('paid','unpaid')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (process_id) REFERENCES processes(id),
    FOREIGN KEY (seller_company_id) REFERENCES companies(id),
    FOREIGN KEY (buyer_company_id) REFERENCES companies(id)
    );
    """
    try:
        with connection:
            connection.execute(query)
        print('Table invoices was created')
    except Exception as e:
        print(f'Error: {e}')
        raise

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
    payment_date DATE,

    FOREIGN KEY (process_id) REFERENCES processes(id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (from_company_id) REFERENCES companies(id),
    FOREIGN KEY (to_company_id) REFERENCES companies(id)
    );
    """
    try:
        with connection:
            connection.execute(query)
        print('Table payments was created')
    except Exception as e:
        print(f'Error: {e}')
        raise

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
    try:
        with connection:
            connection.execute(query)
        print('Table events was created')
    except Exception as e:
        print(f'Error: {e}')
        raise

def create_indexes(connection):
    queries = [
        "CREATE INDEX IF NOT EXISTS idx_process_number ON processes(process_number)",
        "CREATE INDEX IF NOT EXISTS idx_invoice_process ON invoices(process_id)",
        "CREATE INDEX IF NOT EXISTS idx_payment_process ON payments(process_id)",
        "CREATE INDEX IF NOT EXISTS idx_events_process ON events(process_id)"
    ]

    with connection:
        for query in queries:
            connection.execute(query)
    print("Indexes created")

def create_suppliers(connection):

    query = """
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        process_id INTEGER,
        supplier_name TEXT,

        FOREIGN KEY (process_id) REFERENCES processes(id)
    )
    """

    with connection:
        connection.execute(query)

def main():
    connection = get_connection('DATABASE.db')
    try:
        create_users(connection)
        create_companies(connection)
        create_processes(connection)
        create_invoices(connection)
        create_payments(connection)
        create_events(connection)
        create_indexes(connection)
        create_suppliers(connection)
    finally:
        connection.close()

if __name__ == "__main__":
    main()