import sqlite3

def init_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
    CREATE TABLE states (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL,
        line INTEGER,
        var TEXT,
        value BLOB
    )
    """)
    return conn