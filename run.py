"""CLI runner and demo for PyChronicle Time-Travel Tracer."""
import sys
import os
from pychronicle.tracer import PyChronicleTracer

def run_demo(target="bubble_sort"):
    samples = {
        "bubble_sort": (
            "Bubble Sort",
            """arr = [64, 34, 25, 12, 22, 11, 90]
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
        ),
        "fibonacci": (
            "Fibonacci Sequence",
            """def generate_fib(n):
    sequence = [0, 1]
    for _ in range(n - 2):
        sequence.append(sequence[-1] + sequence[-2])
    return sequence

result = generate_fib(8)
print("Fibonacci Result:", result)
"""
        ),
        "binary_search": (
            "Binary Search",
            """def binary_search(arr, target):
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1

nums = [10, 20, 30, 40, 50, 60, 70, 80]
pos = binary_search(nums, 50)
print(f"Element found at index: {pos}")
"""
        ),
        "matrix_mutator": (
            "2D Matrix Transformation",
            """matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]
for r in range(len(matrix)):
    for c in range(len(matrix[0])):
        if r == c:
            matrix[r][c] *= 10
print("Transformed Matrix:", matrix)
"""
        )
    }

    # Check if target is a file path
    if os.path.exists(target):
        title = os.path.basename(target)
        with open(target, "r", encoding="utf-8") as f:
            code = f.read()
    elif target in samples:
        title, code = samples[target]
    else:
        title, code = samples["bubble_sort"]

    print("=" * 72)
    print(f"  PyChronicle Time-Travel Tracer — Running: {title}")
    print("=" * 72)
    print("\n--- Source Code ---")
    for idx, line in enumerate(code.strip().split("\n"), 1):
        print(f"{idx:3d} | {line}")

    print("\n--- Executing Trace ---")
    tracer = PyChronicleTracer(script_name=title)
    trace_res = tracer.trace_code(code)

    print(f"Status:          {'SUCCESS' if trace_res['success'] else 'FAILED'}")
    print(f"Total Steps:     {trace_res['total_steps']}")
    print(f"Duration:        {trace_res['duration_ms']} ms")
    print(f"Captured Output: {trace_res['captured_stdout'].strip() or '(None)'}")

    print("\n--- Step-by-Step State Timeline (Sample of Steps) ---")
    steps = tracer.db.get_all_steps(trace_res["exec_id"])
    
    # Sample steps if there are many
    sample_indices = list(range(min(6, len(steps))))
    if len(steps) > 12:
        sample_indices.extend([len(steps) // 2])
        sample_indices.extend(range(len(steps) - 5, len(steps)))
    sample_indices = sorted(list(set(sample_indices)))

    for i in sample_indices:
        step = steps[i]
        deltas_str = ", ".join([f"{d['var_name']} = {d['value_repr']}" for d in step["deltas"]]) if step["deltas"] else "no change"
        code_line = (step['code_line'] or '').strip()
        s_id = step.get('step_id') or step.get('step_number') or (i + 1)
        print(f"Step {s_id:3d} (Line {step['line_number']:2d}): {code_line:<35} | Delta: {deltas_str}")

    if len(steps) > len(sample_indices):
        print(f"... ({len(steps) - len(sample_indices)} intermediate steps recorded in trace database)")

    print("\n" + "=" * 72)
    print("Time-travel execution trace completed successfully.")
    print("=" * 72)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "bubble_sort"
    run_demo(target)
