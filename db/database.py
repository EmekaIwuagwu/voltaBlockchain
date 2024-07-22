import sqlite3

DATABASE = 'volta_blockchain_db.db'

def create_tables():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        address TEXT PRIMARY KEY,
        passkey TEXT NOT NULL,
        uuid TEXT NOT NULL,
        balance REAL NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        txHash TEXT PRIMARY KEY,
        addressFrom TEXT NOT NULL,
        addressTo TEXT NOT NULL,
        amount REAL NOT NULL,
        dateOfTransaction TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (addressFrom) REFERENCES users (address),
        FOREIGN KEY (addressTo) REFERENCES users (address)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS blocks (
        BlockID INTEGER PRIMARY KEY AUTOINCREMENT,
        Timestamp TEXT NOT NULL,
        Hash TEXT NOT NULL,
        PreviousHash TEXT NOT NULL,
        address TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (address) REFERENCES users (address)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS loans (
        LoanId INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT NOT NULL,
        amount REAL NOT NULL,
        LoanReasons TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (address) REFERENCES users (address)
    )
    ''')

    connection.commit()
    connection.close()
