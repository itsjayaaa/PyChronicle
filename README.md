# PyChronicle

# AST Module :


import ast, sys, sqlite3, time

db = sqlite3.connect(":memory:")
db.execute("""CREATE TABLE states (
    ts REAL, line INTEGER, var TEXT, value TEXT
)""")

def tracefunc(frame, event, arg):
    if event == "line":
        lineno = frame.f_lineno
        for var, val in frame.f_locals.items():
            db.execute("INSERT INTO states VALUES (?, ?, ?, ?)",
                       (time.time(), lineno, var, repr(val)))
    return tracefunc

def run_script(path):
    sys.settrace(tracefunc)
    with open(path) as f:
        code = f.read()
    exec(code, {})

# Example usage
run_script("target.py")
for row in db.execute("SELECT * FROM states LIMIT 10"):
    print(row)

# AST Parsing :

import ast
class AssignmentVisitor(ast.NodeVisitor):
    def __init__(self):
        self.assignments = []

    def visit_Assign(self, node):
        # Capture variable names and line numbers
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assignments.append((target.id, node.lineno))
        self.generic_visit(node)

def parse_file(path):
    with open(path, "r") as f:
        tree = ast.parse(f.read(), filename=path)
    visitor = AssignmentVisitor()
    visitor.visit(tree)
    return visitor.assignments

# Example usage
assigns = parse_file("target.py")
print("Assignments found:", assigns)

# Storage Schema :

import sqlite3

def init_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE states (
            ts REAL,
            line INTEGER,
            var TEXT,
            value TEXT
        )
    """)
    return conn

# Example insert
db = init_db()
db.execute("INSERT INTO states VALUES (?, ?, ?, ?)", (123.45, 2, "x", "10"))
db.commit()

for row in db.execute("SELECT * FROM states"):
    print(row)





