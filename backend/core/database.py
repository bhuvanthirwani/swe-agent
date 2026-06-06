import sqlite3
import os

DATABASE_PATH = os.getenv("DATABASE_PATH", "swe_agent.db")

db_initialized = False

def get_db_connection():
    global db_initialized
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    
    if not db_initialized:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agents'")
        if not cursor.fetchone():
            schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    conn.executescript(f.read())
                    conn.commit()
        db_initialized = True
        
    return conn

def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if not os.path.exists(schema_path):
        print(f"Schema file not found at {schema_path}")
        return

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_script = f.read()

    conn = get_db_connection()
    try:
        conn.executescript(schema_script)
        conn.commit()
        print(f"Database initialized successfully at {DATABASE_PATH}.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
