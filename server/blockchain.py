import sqlite3
import hashlib
import uuid
import json
from datetime import datetime

DATABASE = 'volta_blockchain_db.db'

def sha256_hash(data):
    return hashlib.sha256(data.encode()).hexdigest()

def generate_address(is_admin=False):
    prefix = "VTA" if is_admin else "VT"
    return prefix + hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:26]

def create_admin_account():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    admin_address = generate_address(is_admin=True)
    admin_passkey = hashlib.sha256(b"passkey").hexdigest()
    admin_uuid = str(uuid.uuid4())
    initial_balance = float("1e19")

    cursor.execute('''
    INSERT INTO users (address, passkey, uuid, balance, created_at)
    VALUES (?, ?, ?, ?, datetime('now'))
    ''', (admin_address, admin_passkey, admin_uuid, initial_balance))

    connection.commit()
    connection.close()

    print(f"Admin created: {admin_address}, {admin_passkey}, {admin_uuid}, {initial_balance}")

    return {
        "address": admin_address,
        "passkey": admin_passkey,
        "uuid": admin_uuid,
        "balance": initial_balance
    }

def blockchain_initialized():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT * FROM blocks")
    result = c.fetchone()

    conn.close()

    return result is not None

def initialize_blockchain():
    if blockchain_initialized():
        print("Blockchain already initialized. Returning existing data...")
        return None

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    admin_address = generate_address(is_admin=True)
    admin_passkey = hashlib.sha256(b"passkey").hexdigest()
    admin_uuid = str(uuid.uuid4())
    initial_supply = float("1e19")

    c.execute("INSERT INTO users (address, passkey, uuid, balance, created_at) VALUES (?, ?, ?, ?, ?)",
              (admin_address, admin_passkey, admin_uuid, initial_supply, datetime.now()))

    genesis_block = {
        "Genesis Token": "VOLTA",
        "Timestamp": str(datetime.now()),
        "Date": datetime.now().date().isoformat(),
        "Author": "Volta",
        "TokenName": "VOLTA",
        "TokenCurrency": "VOLTGX",
        "TokenSupply": initial_supply,
        "Address": admin_address
    }

    genesis_block_json = json.dumps(genesis_block)
    genesis_block_hash = sha256_hash(genesis_block_json)

    c.execute("INSERT INTO blocks (Timestamp, Hash, PreviousHash, address, created_at) VALUES (?, ?, ?, ?, ?)",
              (datetime.now(), genesis_block_hash, "0", admin_address, datetime.now()))

    conn.commit()
    conn.close()

    return genesis_block_json


def create_address():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    user_address = generate_address()
    user_passkey = hashlib.sha256(str(uuid.uuid4().int % 10).encode()).hexdigest()
    user_uuid = str(uuid.uuid4())
    initial_balance = 0.0

    c.execute("INSERT INTO users (address, passkey, uuid, balance, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_address, user_passkey, user_uuid, initial_balance, datetime.now()))

    conn.commit()
    conn.close()

    return {
        "address": user_address,
        "balance": initial_balance,
        "uuid": user_uuid,
        "passkey": user_passkey
    }

def get_last_block():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT * FROM blocks ORDER BY BlockID DESC LIMIT 1")
    last_block = c.fetchone()

    conn.close()

    return last_block

def add_block(transactions):
    last_block = get_last_block()
    previous_hash = last_block[2] if last_block else "0"

    new_block = {
        "Timestamp": str(datetime.now()),
        "Transactions": transactions,
        "PreviousHash": previous_hash
    }

    new_block_json = json.dumps(new_block)
    new_block_hash = sha256_hash(new_block_json)

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("INSERT INTO blocks (Timestamp, Hash, PreviousHash, created_at) VALUES (?, ?, ?, ?)",
              (datetime.now(), new_block_hash, previous_hash, datetime.now()))

    conn.commit()
    conn.close()

    return new_block


def create_transaction(address_from, address_to, amount, passkey):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE address=?", (address_from,))
    sender = c.fetchone()
    c.execute("SELECT * FROM users WHERE address=?", (address_to,))
    receiver = c.fetchone()

    if not sender or not receiver:
        conn.close()
        return {"error": "Invalid addresses"}
    
    if sender[1] != passkey:
        conn.close()
        return {"error": "Invalid passkey"}

    if sender[3] < amount:
        conn.close()
        return {"error": "Insufficient balance"}

    c.execute("SELECT * FROM loans WHERE address=? AND status='active'", (address_from,))
    active_loans = c.fetchall()
    if active_loans:
        conn.close()
        return {"error": "Loan Tokens cannot be withdrawn, they can only be used for VOLTA Sponsored businesses."}

    new_sender_balance = sender[3] - amount
    new_receiver_balance = receiver[3] + amount

    c.execute("UPDATE users SET balance=? WHERE address=?", (new_sender_balance, address_from))
    c.execute("UPDATE users SET balance=? WHERE address=?", (new_receiver_balance, address_to))

    transaction = {
        "from": address_from,
        "to": address_to,
        "amount": amount,
        "date": str(datetime.now())
    }

    transaction_json = json.dumps(transaction)
    transaction_hash = sha256_hash(transaction_json)

    c.execute("INSERT INTO transactions (txHash, addressFrom, addressTo, amount, dateOfTransaction, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (transaction_hash, address_from, address_to, amount, datetime.now(), datetime.now()))

    conn.commit()
    conn.close()

    # Add transaction to block
    add_block([transaction])

    return {"success": True, "new_balance": new_sender_balance, "txHash": transaction_hash}

def check_balance(address):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE address=?", (address,))
    balance = c.fetchone()

    conn.close()

    if balance:
        return {"balance": balance[0]}
    else:
        return {"error": "Invalid address"}

def check_transactions(address):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT * FROM transactions WHERE addressFrom=? OR addressTo=?", (address, address))
    transactions = c.fetchall()

    conn.close()

    if transactions:
        return {"transactions": [{"from": tx[1], "to": tx[2], "amount": tx[3], "date": tx[4]} for tx in transactions]}
    else:
        return {"error": "No transactions found"}

def request_loan(address, amount, reason):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("INSERT INTO loans (address, amount, LoanReasons, status, created_at) VALUES (?, ?, ?, 'active', ?)",
              (address, amount, reason, datetime.now()))

    c.execute("SELECT balance FROM users WHERE address=?", (address,))
    balance = c.fetchone()[0]
    new_balance = balance + amount

    c.execute("UPDATE users SET balance=? WHERE address=?", (new_balance, address))

    # Create a loan transaction
    transaction = {
        "from": "LOAN_SYSTEM",
        "to": address,
        "amount": amount,
        "date": str(datetime.now())
    }

    transaction_json = json.dumps(transaction)
    transaction_hash = sha256_hash(transaction_json)

    c.execute("INSERT INTO transactions (txHash, addressFrom, addressTo, amount, dateOfTransaction, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (transaction_hash, "LOAN_SYSTEM", address, amount, datetime.now(), datetime.now()))

    conn.commit()
    conn.close()

    # Add loan transaction to block
    add_block([transaction])

    return {"message": "Loan requested successfully", "previous_balance": balance, "updated_balance": new_balance, "txHash": transaction_hash}

def pay_back_loan(address, amount):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT * FROM loans WHERE address=? AND status='active'", (address,))
    active_loan = c.fetchone()

    if not active_loan:
        conn.close()
        return {"error": "No active loan found"}

    c.execute("UPDATE loans SET status='paid', created_at=? WHERE LoanId=?", (datetime.now(), active_loan[0]))

    c.execute("SELECT balance FROM users WHERE address=?", (address,))
    balance = c.fetchone()[0]
    new_balance = balance - amount

    c.execute("UPDATE users SET balance=? WHERE address=?", (new_balance, address))

    # Create a loan repayment transaction
    transaction = {
        "from": address,
        "to": "LOAN_SYSTEM",
        "amount": amount,
        "date": str(datetime.now())
    }

    transaction_json = json.dumps(transaction)
    transaction_hash = sha256_hash(transaction_json)

    c.execute("INSERT INTO transactions (txHash, addressFrom, addressTo, amount, dateOfTransaction, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (transaction_hash, address, "LOAN_SYSTEM", amount, datetime.now(), datetime.now()))

    conn.commit()
    conn.close()

    # Add loan repayment transaction to block
    add_block([transaction])

    return {"message": "Loan paid back successfully", "previous_balance": balance, "updated_balance": new_balance, "txHash": transaction_hash}
