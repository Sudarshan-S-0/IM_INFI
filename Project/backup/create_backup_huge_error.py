import sqlite3
import hashlib
from pathlib import Path

def generate_huge_database(db_path: Path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
        
    print(f"Generating huge database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            price REAL NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    
    # Insert 50,000 rows
    total_rows = 50000
    
    # 1. Users
    print("Inserting 50,000 users...")
    users_data = [(f"User_{i}", f"user_{i}@example.com") for i in range(1, total_rows + 1)]
    cursor.executemany("INSERT INTO users (name, email) VALUES (?, ?);", users_data)
    
    # 2. Products
    print("Inserting 50,000 products...")
    products_data = [(f"Product_{i}", float(i * 10)) for i in range(1, total_rows + 1)]
    cursor.executemany("INSERT INTO products (product_name, price) VALUES (?, ?);", products_data)
    
    # 3. Orders
    print("Inserting 50,000 orders...")
    orders_data = [(i, float(i * 5)) for i in range(1, total_rows + 1)]
    cursor.executemany("INSERT INTO orders (user_id, amount) VALUES (?, ?);", orders_data)
    
    conn.commit()
    
    # Calculate checksums on the pristine database
    print("Calculating checksums on pristine database...")
    checksums = {}
    conn.row_factory = sqlite3.Row
    val_cursor = conn.cursor()
    
    for table in ["users", "products", "orders"]:
        val_cursor.execute(f"SELECT * FROM {table} ORDER BY id;")
        hasher = hashlib.sha256()
        while True:
            rows = val_cursor.fetchmany(1000)
            if not rows:
                break
            for row in rows:
                hasher.update(str(tuple(row)).encode("utf-8"))
        checksums[table] = hasher.hexdigest()
        
    print(f"Pristine Checksums:\n {checksums}")
    
    # Intentionally corrupt data in database: change email of user 25000
    print("Tampering with user 25000 to trigger checksum mismatch failure...")
    cursor.execute("UPDATE users SET email = 'tampered@hacker.com' WHERE id = 25000;")
    conn.commit()
    
    # Let's verify and output tampered checksum for user table
    val_cursor.execute("SELECT * FROM users ORDER BY id;")
    hasher = hashlib.sha256()
    while True:
        rows = val_cursor.fetchmany(1000)
        if not rows:
            break
        for row in rows:
            hasher.update(str(tuple(row)).encode("utf-8"))
    tampered_checksum = hasher.hexdigest()
    print(f"Tampered users checksum is: {tampered_checksum}")
    
    conn.close()
    return checksums

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    db_file = project_root / "backup" / "backup_huge_error.db"
    generate_huge_database(db_file)
