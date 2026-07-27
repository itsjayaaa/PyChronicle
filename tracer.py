import sys
import io

steps = []

def trace_execution(code):
    global steps
    steps = []

    output_buffer = io.StringIO()

    def tracer(frame, event, arg):
        if event != "line":
            return tracer

        lineno = frame.f_lineno

        # Get variables
        local_vars = frame.f_locals.copy()
        clean_vars = {}

        for k, v in local_vars.items():
            if not k.startswith("__"):
                try:
                    clean_vars[k] = repr(v)
                except:
                    pass

        # Get current line code
        lines = code.splitlines()
        line_code = lines[lineno - 1].strip() if lineno <= len(lines) else ""

        # Get FULL output till now
        current_output = output_buffer.getvalue()

        steps.append({
            "line": lineno,
            "code": line_code,
            "vars": clean_vars,
            "output": current_output
        })

        return tracer

    # Redirect stdout
    original_stdout = sys.stdout
    sys.stdout = output_buffer

    # Run traced code
    sys.settrace(tracer)
    exec(code, {})
    sys.settrace(None)

    # Restore stdout
    sys.stdout = original_stdout

    return steps