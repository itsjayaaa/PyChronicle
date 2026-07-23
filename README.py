# PyChronicle

# AST module :

import ast, sys, sqlite3, time

db = sqlite3.connect(":memory:")
db.execute("""CREATE TABLE states(
    ts REAL, line INTEGER, var TEXT, value TEXT
)""")

def tracefun(frame, event, arg):
    if event == "line":
        lineno = frame.f_lineno
        for var, val in frame.f_locals.items():
            db.execute("INSERT INTO states VALUES (?, ?, ?, ?)",
                       (time.time(), lineno, var, repr(val)))
    return tracefun 

def run_script(path):
    sys.settrace(tracefun)
    with open(path) as f:
        code = f.read()
    exec(code, {}) 

# Example usage
run_script("target.py") 
for row in db.execute("SELECT * FROM states LIMIT 10"):
    print(row)



# AST parsing :


import ast

class AssignmentVistor(ast.NodeVisitor):
    def __init__(self):
        self.assignments = []

    def visit_Assign(self, node):
        # capture variable names and line numbers
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assignments.append((target.id, node.lineno))
        self.generic_visit(node)

def parse_file(path):
    with open(path, "r") as f:
        tree = ast.parse(f.read(), filename=path)
    Vistor = AssignmentVistor()
    Vistor.visit(tree)
    return Vistor.assignments

# Example usage
assigns = parse_file("target.py")
print("assignments found:", assigns) 



# Storage Schema :

import sqlite3

def init_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE states (
            its REAL,
            line INTEGER,
            var TEXT,
            value TEXT
        )
    """)
    return conn

# Example insert
db = init_db
db.execute("INSERT INTO states VALUES (?, ?, ?, ?)", (123.45, 2, "x", "10"))
db.commit()

for row in db.execute("SELECT * FROM states"):
    print(row)


# Sys.settrace :


import sys, time, sqlite3, zlib, pickle

db = sqlite3.connect(":memory:")
db.execute(""" CREATE TABLE states (
    id INTEGER PRIMER KEY AUTOINCREMENT,
    ts REAL, line INTEGER, var TEXT, value BLOB
)""")

_last_values = {}

def tracefun(frame, event, arg):
    if event == "line":
        lineno = frame.f_lineno
        for var, val in frame.f_locals.items():
            prev = _last_values.get(var)
            if prev != val: # delta compression
                blob = zlib.compress(pickle.dumps(val))
                db.execute("INSERT INTO states ts, line, var, value) VALUES(?, ?, ?, ?)",
                           (time.time(), lineno, var, blob))
                _last_values[var] = val
    return tracefun

def run_script(path):
    sys.settrace(tracefun)
    with open(path) as f:
        code = f.read()
    exec(code, {})
    sys.settrace(None)

# Textual App Layout :

from textual.app import App, ComposeResult
from textual.widgets import Static, Slider

class PyChronicleUI(App):
    CSS_PATH = "pychronicle.css"

    def compose(self) -> ComposeResult:
        yield Static("code view", id ="code")
        yield Slider(id="timeline", min=0, max=100)

    def on_slider_changed(self, event: Slider.Changed) -> None:
        ts = event.value
        # query SQLite for nearest timestamp 
        row = db.execute("SELECT line, var, val FROM states WHERE ts <= ? ORDER BY ts DESC LIMIT 1",(ts,)).fetchone()
        if row:
            self.query_one("#code", Static).update(f"Line {row[0]} | {row[1]} ={pickle.loads(zlib.decompress(row[2]))}")

if __name__ == "__main__":
    PyChronicleUI().run()

# Textual UI Scaffolding:

from textual.app import App, ComposeResult
from textual.widgets import Static, Slider
import sqlite3, pickle, zlib

# Assume db is already populated by tracer
db = sqlite3.connect(":memory:")

class PyChronicleUI(App):
    CSS_PATH = None # you can add a CSS file later for styling

    def compose(self) -> ComposeResult:
        yield Static("Code View", id="code")
        yield Slider(id="time line", min=0, max=100)

    def on_slider_changed(self, event: Slider.Changed) -> None:
        ts = event.value
        # query SQLite for nearest timestamp
        row = db.execute(
            "SELECT line, var, value FROM states WHERE ts <= ? ORDER BY ts DESC LIMIT 1",
            (ts,)
        ).fetchone()
        if row:
            line, var, blob = row
            val = pickle.loads(zlib.decompress(blob))
            self.query_one("#code", Static).update(
                f"LINE {line} | {var} = {val}"
            )
if __name__ == "__main__":
    PyChronicleUI().run()
                       