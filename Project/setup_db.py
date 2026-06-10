import os
import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    db_dir = os.path.join(os.path.dirname(__file__), 'backup')
    db_path = os.path.join(db_dir, 'backup.db')
    sql_path = os.path.join(db_dir, 'create_backup.sql')

    # Ensure backup directory exists
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        logger.info(f"Created directory: {db_dir}")

    logger.info("Initializing database...")

    try:
        # Read the SQL creation script
        with open(sql_path, 'r') as sql_file:
            sql_script = sql_file.read()

        # Connect to SQLite database (creates file if it does not exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Execute the SQL script
        cursor.executescript(sql_script)
        conn.commit()

        logger.info(f"Database successfully created and populated at {db_path}")

        # Basic validation print
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        logger.info(f"Tables created: {[t[0] for t in tables if not t[0].startswith('sqlite_')]}")

        for table in ['users', 'orders', 'products']:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            logger.info(f"Table '{table}' has {count} rows.")

        conn.close()
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        raise

if __name__ == "__main__":
    main()
