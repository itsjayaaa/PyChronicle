from tracer import trace_execution
from ui import run_ui

TARGET_FILE = "target.py"

if __name__ == "__main__":
    with open(TARGET_FILE) as f:
        code = f.read()

    steps = trace_execution(code)

    run_ui(steps, code)