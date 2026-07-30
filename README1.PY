# ----------------------------
# Storage Schema
# ----------------------------
import sqlite3

def init_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE states(
            ts REAL,
            line INTEGER,
            var TEXT,
            value TEXT
        )
    """)
    return conn

# ------------------------
# INSERT
# ------------------------
db = init_db()
db.execute("INSERT INTO states VALUES (?, ?, ?, ?)", (123.45, 2, "x", "10"))
db.commit()

for row in db.execute("SELECT * FROM states"):
    print(row)
