# ==============================
# PyChronicle - Clean Version
# ==============================

import sys
import time
import sqlite3
import pickle
import zlib
import ast
import os

# ------------------------------
# DATABASE SETUP
# ------------------------------
db = sqlite3.connect(":memory:")
db.execute("""
CREATE TABLE states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    line INTEGER,
    var TEXT,
    value BLOB
)
""")

# ------------------------------
# TRACE FUNCTION (FILTERED)
# ------------------------------
_last_values = {}
TARGET_FILE = None  # will set dynamically


def tracefun(frame, event, arg):
    if event == "line":

        # ✅ Only trace target file
        filename = frame.f_code.co_filename
        if not filename.endswith(TARGET_FILE):
            return tracefun

        lineno = frame.f_lineno

        for var, val in frame.f_locals.items():

            # ✅ Skip unwanted variables
            if var.startswith("__"):
                continue
            if var in ("__builtins__",):
                continue

            prev = _last_values.get(var)

            if prev != val:
                try:
                    blob = zlib.compress(pickle.dumps(val))
                except:
                    continue

                db.execute(
                    "INSERT INTO states (ts, line, var, value) VALUES (?, ?, ?, ?)",
                    (time.time(), lineno, var, blob)
                )

                _last_values[var] = val

    return tracefun


# ------------------------------
# RUN TARGET SCRIPT
# ------------------------------
def run_script(path):
    global TARGET_FILE

    TARGET_FILE = os.path.basename(path)

    sys.settrace(tracefun)

    with open(path, "r") as f:
        code = f.read()

    exec(compile(code, path, "exec"), {})

    sys.settrace(None)


# ------------------------------
# AST PARSER
# ------------------------------
class AssignmentVisitor(ast.NodeVisitor):
    def __init__(self):
        self.assignments = []

    def visit_Assign(self, node):
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


# ------------------------------
# PRINT TRACE
# ------------------------------
def print_states(limit=20):
    print("\n--- Execution Trace ---")

    for row in db.execute(
        "SELECT ts, line, var, value FROM states ORDER BY ts LIMIT ?",
        (limit,)
    ):
        ts, line, var, blob = row
        val = pickle.loads(zlib.decompress(blob))
        print(f"Line {line} | {var} = {val}")


# ------------------------------
# MAIN
# ------------------------------
if __name__ == "__main__":
    target_file = "target.py"

    print("Running PyChronicle...\n")

    # Run tracing
    run_script(target_file)

    # Show results
    print_states()

    # Static analysis
    assigns = parse_file(target_file)
    print("\n--- Static Assignments ---")
    print(assigns)