"""
PyChronicle Main CLI & JSON API Bridge
Connects Python execution tracer engine with Node/Express web server and CLI.
"""

import sys
import os
import json
import argparse
from typing import Dict, Any

# Ensure pychronicle package is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pychronicle.tracer import PyChronicleTracer
from pychronicle.ast_rewriter import analyze_ast
from pychronicle.graphs import SVGGraphGenerator

SAMPLE_SCRIPTS = {
    "bubble_sort": {
        "name": "Bubble Sort Array Mutation",
        "code": """# Bubble Sort Array Mutation
arr = [64, 34, 25, 12, 22, 11, 90]
n = len(arr)

for i in range(n):
    swapped = False
    for j in range(0, n - i - 1):
        if arr[j] > arr[j + 1]:
            arr[j], arr[j + 1] = arr[j + 1], arr[j]
            swapped = True
    if not swapped:
        break

print("Sorted Array:", arr)
"""
    },
    "fibonacci": {
        "name": "Fibonacci Sequence Delta State",
        "code": """# Fibonacci State Progression
def fibonacci(n):
    a, b = 0, 1
    sequence = [a]
    for i in range(1, n):
        sequence.append(b)
        a, b = b, a + b
    return sequence

result = fibonacci(8)
print("Fibonacci Result:", result)
"""
    },
    "binary_search": {
        "name": "Binary Search Pointer Shifts",
        "code": """# Binary Search Pointer Delta Debugging
items = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
target = 23

low = 0
high = len(items) - 1
found_index = -1

while low <= high:
    mid = (low + high) // 2
    guess = items[mid]
    
    if guess == target:
        found_index = mid
        break
    elif guess < target:
        low = mid + 1
    else:
        high = mid - 1

print("Found index:", found_index)
"""
    },
    "matrix_mutator": {
        "name": "2D Matrix Transformation",
        "code": """# 2D Matrix State Mutations
matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]

rows = len(matrix)
cols = len(matrix[0])
transposed = [[0] * rows for _ in range(cols)]

for r in range(rows):
    for c in range(cols):
        transposed[c][r] = matrix[r][c]

print("Transposed Matrix:", transposed)
"""
    }
}


def run_tracer_json(source_code: str, script_name: str = "script.py") -> Dict[str, Any]:
    tracer = PyChronicleTracer(script_name=script_name)
    res = tracer.trace_code(source_code)
    
    if not res["success"] and res.get("error"):
        return res

    exec_id = res["exec_id"]
    steps = tracer.db.get_all_steps(exec_id)
    ast_res = res["ast_analysis"]

    # Gather watched variables automatically
    vars_found = ast_res.get("variables", [])
    var_timelines = {}
    for v in vars_found:
        var_timelines[v] = tracer.db.get_variable_timeline(exec_id, v)

    # Generate SVGs
    timeline_svg = SVGGraphGenerator.generate_variable_timeline_svg(
        steps=steps,
        var_timelines=var_timelines,
        watched_vars=vars_found[:5]
    )

    heatmap_svg = SVGGraphGenerator.generate_execution_flow_heatmap_svg(
        steps=steps,
        total_lines=res["total_lines"]
    )

    res["steps"] = steps
    res["variable_names"] = vars_found
    res["timeline_svg"] = timeline_svg
    res["heatmap_svg"] = heatmap_svg

    return res


def main():
    parser = argparse.ArgumentParser(description="PyChronicle CLI & API Bridge")
    parser.add_argument("action", nargs="?", default="trace", choices=["trace", "sample", "ast", "step"], help="Action to perform")
    parser.add_argument("--code", type=str, help="Python source code to trace")
    parser.add_argument("--file", type=str, help="Python file path")
    parser.add_argument("--sample_key", type=str, help="Sample script key")
    parser.add_argument("--step_id", type=int, default=1, help="Step ID to inspect")
    parser.add_argument("--summary", action="store_true", help="Print human-readable text summary instead of raw JSON")
    parser.add_argument("--format", choices=["json", "table", "summary"], default="json", help="Output format")

    args = parser.parse_args()

    if args.action == "sample":
        if args.sample_key and args.sample_key in SAMPLE_SCRIPTS:
            print(json.dumps(SAMPLE_SCRIPTS[args.sample_key]))
        else:
            print(json.dumps(SAMPLE_SCRIPTS))
        return

    code = ""
    script_title = "Custom Script"
    if args.file and os.path.exists(args.file):
        script_title = os.path.basename(args.file)
        with open(args.file, "r", encoding="utf-8") as f:
            code = f.read()
    elif args.code:
        code = args.code
    elif args.sample_key and args.sample_key in SAMPLE_SCRIPTS:
        script_title = SAMPLE_SCRIPTS[args.sample_key]["name"]
        code = SAMPLE_SCRIPTS[args.sample_key]["code"]
    else:
        # Read stdin if no code provided
        if not sys.stdin.isatty():
            code = sys.stdin.read()

    if not code:
        print(json.dumps({"error": "No Python code provided"}))
        sys.exit(1)

    if args.action == "ast":
        res = analyze_ast(code)
        print(json.dumps(res))
        return
        
    if args.action == "trace":
        res = run_tracer_json(code, script_name=script_title)
        
        # If user requested human-readable summary/table format
        if args.summary or args.format in ["table", "summary"]:
            print("=" * 72)
            print(f"  PyChronicle Time-Travel Tracer — {script_title}")
            print("=" * 72)
            print(f"Status:          {'SUCCESS' if res.get('success') else 'FAILED'}")
            print(f"Total Steps:     {res.get('total_steps', 0)}")
            print(f"Duration:        {res.get('duration_ms', 0)} ms")
            print(f"Captured Output: {res.get('captured_stdout', '').strip() or '(None)'}")
            print("\n--- Step-by-Step State Timeline ---")
            steps = res.get("steps", [])
            
            # Show sampled or all steps
            step_sample = steps
            if len(steps) > 15:
                step_sample = steps[:6] + [steps[len(steps)//2]] + steps[-6:]
                
            for step in step_sample:
                deltas = step.get("deltas", [])
                deltas_str = ", ".join([f"{d.get('var_name')} = {d.get('value_repr')}" for d in deltas]) if deltas else "no change"
                code_line = (step.get('code_line') or '').strip()[:35]
                s_id = step.get('step_id') or step.get('step_number') or 1
                print(f"Step {s_id:3d} (Line {step.get('line_number', 0):2d}): {code_line:<35} | Delta: {deltas_str}")
            if len(steps) > 15:
                print(f"... ({len(steps) - 13} intermediate steps recorded in trace database)")
            print("=" * 72)
        else:
            print(json.dumps(res))


if __name__ == "__main__":
    main()
