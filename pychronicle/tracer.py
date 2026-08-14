"""
PyChronicle Tracer Engine
Uses sys.settrace to wrap Python execution, capturing variable deltas and state snapshots.
"""

import sys
import os
import time
import json
import io
import traceback
from typing import Dict, Any, List, Optional, Tuple
from pychronicle.db import StateDatabase
from pychronicle.ast_rewriter import analyze_ast

def safe_serialize_val(val: Any, max_len: int = 250) -> Tuple[str, str, Dict[str, Any]]:
    """Safely computes a string representation, type, and structural detail of any Python value."""
    val_type = type(val).__name__
    meta: Dict[str, Any] = {}
    try:
        if isinstance(val, (int, float, bool, type(None))):
            s = str(val)
            meta["is_numeric"] = isinstance(val, (int, float)) and not isinstance(val, bool)
            meta["raw_val"] = val
        elif isinstance(val, str):
            s = f'"{val}"'
            meta["raw_val"] = val
            meta["length"] = len(val)
        elif isinstance(val, list):
            s = repr(val)
            meta["is_list"] = True
            meta["length"] = len(val)
            # Check if 2D matrix
            if len(val) > 0 and isinstance(val[0], list):
                meta["is_matrix"] = True
                meta["rows"] = len(val)
                meta["cols"] = len(val[0]) if len(val) > 0 else 0
                meta["matrix_rows"] = [[repr(item) for item in row[:15]] for row in val[:15]]
            else:
                meta["elements"] = [repr(x) for x in val[:50]]
        elif isinstance(val, (tuple, set)):
            s = repr(val)
            meta["is_list"] = True
            meta["length"] = len(val)
            meta["elements"] = [repr(x) for x in list(val)[:50]]
        elif isinstance(val, dict):
            s = repr(val)
            meta["is_dict"] = True
            meta["length"] = len(val)
            meta["keys"] = [str(k) for k in list(val.keys())[:30]]
        else:
            s = repr(val)
        
        if len(s) > max_len:
            s = s[:max_len] + "..."
        return s, val_type, meta
    except Exception:
        return "<unserializable>", val_type, {}


class PyChronicleTracer:
    def __init__(self, script_name: str = "script.py", max_steps: int = 1500):
        self.script_name = script_name
        self.max_steps = max_steps
        self.db = StateDatabase(":memory:")
        self.step_count = 0
        self.start_time = 0.0
        self.exec_id = 0
        self.previous_variables: Dict[str, str] = {}
        self.code_lines: List[str] = []
        self.filename = ""
        self.captured_io: Optional[io.StringIO] = None

    def trace_code(self, source_code: str) -> Dict[str, Any]:
        """Executes source code under sys.settrace and records state deltas in SQLite."""
        self.code_lines = source_code.splitlines()
        ast_result = analyze_ast(source_code)
        
        ast_json = json.dumps(ast_result.get("ast_tree", {})) if ast_result["success"] else "{}"
        self.exec_id = self.db.create_execution(
            script_name=self.script_name,
            total_lines=len(self.code_lines),
            ast_json=ast_json
        )

        self.step_count = 0
        self.previous_variables = {}
        self.start_time = time.perf_counter()

        # Compile code object
        try:
            compiled_code = compile(source_code, "<string>", "exec")
        except Exception as e:
            return {
                "success": False,
                "error": f"Compilation Error: {str(e)}",
                "traceback": traceback.format_exc()
            }

        globals_dict = {
            "__name__": "__main__",
            "__doc__": None,
            "__package__": None,
        }

        old_trace = sys.gettrace()
        old_stdout = sys.stdout
        self.captured_io = io.StringIO()
        
        try:
            sys.stdout = self.captured_io
            sys.settrace(self._trace_dispatch)
            exec(compiled_code, globals_dict)
        except Exception as e:
            # Capture final exception line if raised
            err_msg = str(e)
            tb = traceback.format_exc()
        else:
            err_msg = None
            tb = None
        finally:
            sys.settrace(old_trace)
            sys.stdout = old_stdout

        captured_stdout = self.captured_io.getvalue()
        
        # If execution succeeded, add a final step for program completion
        if not err_msg and self.step_count > 0:
            self.step_count += 1
            final_vars = []
            final_deltas = []
            for k, v in globals_dict.items():
                if k.startswith("__"):
                    continue
                v_repr, v_type, v_meta = safe_serialize_val(v)
                prev_val = self.previous_variables.get(k)
                is_changed = (prev_val != v_repr)
                item = {
                    'var_name': k,
                    'var_type': v_type,
                    'value_repr': v_repr,
                    'prev_value_repr': prev_val,
                    'is_changed': is_changed,
                    'scope_type': 'global',
                    'meta': v_meta
                }
                final_vars.append(item)
                if is_changed:
                    final_deltas.append(item)

            timestamp_us = (time.perf_counter() - self.start_time) * 1_000_000
            self.db.record_step(
                exec_id=self.exec_id,
                step_id=self.step_count,
                line_no=len(self.code_lines),
                code_line="🏁 [Execution Completed]",
                func_name="<module>",
                event_type="completed",
                timestamp_us=timestamp_us,
                stack_depth=0,
                stack_json="[]",
                deltas=final_deltas,
                stdout_snapshot=captured_stdout,
                all_vars=final_vars
            )

        exec_duration_ms = (time.perf_counter() - self.start_time) * 1000.0
        self.db.finalize_execution(self.exec_id, self.step_count, exec_duration_ms)

        summary = self.db.get_execution_summary(self.exec_id)
        steps = self.db.get_all_steps(self.exec_id)

        return {
            "success": True if not err_msg else False,
            "error": err_msg,
            "traceback": tb,
            "captured_stdout": captured_stdout,
            "exec_id": self.exec_id,
            "total_steps": self.step_count,
            "duration_ms": round(exec_duration_ms, 2),
            "total_lines": len(self.code_lines),
            "code_lines": self.code_lines,
            "ast_analysis": ast_result,
            "initial_step": steps[0] if steps else {}
        }

    def _trace_dispatch(self, frame, event, arg):
        # We only trace execution in the target script (<string>)
        if frame.f_code.co_filename != "<string>":
            return self._trace_dispatch

        if self.step_count >= self.max_steps:
            return None  # Stop tracing to prevent infinite loops

        if event == "line":
            line_no = frame.f_lineno
            if 1 <= line_no <= len(self.code_lines):
                code_line = self.code_lines[line_no - 1].strip()
            else:
                code_line = ""

            self.step_count += 1
            timestamp_us = (time.perf_counter() - self.start_time) * 1_000_000

            # Collect call stack summary
            stack = []
            curr_f = frame
            while curr_f and curr_f.f_code.co_filename == "<string>":
                stack.append({
                    "function": curr_f.f_code.co_name,
                    "line": curr_f.f_lineno
                })
                curr_f = curr_f.f_back

            # Inspect variables in locals and globals
            deltas = []
            all_vars = []
            current_vars = {}

            # First collect globals if running inside function
            scope_dict = {}
            if frame.f_globals:
                for k, v in frame.f_globals.items():
                    if not k.startswith("__") and not callable(v):
                        scope_dict[k] = (v, 'global')
            
            # Overlay locals
            for k, v in frame.f_locals.items():
                if not k.startswith("__"):
                    scope_dict[k] = (v, 'local')

            for var_name, (var_val, scope_type) in scope_dict.items():
                val_repr, val_type, meta = safe_serialize_val(var_val)
                current_vars[var_name] = val_repr
                
                prev_val = self.previous_variables.get(var_name)
                is_changed = (prev_val is not None and prev_val != val_repr)

                var_item = {
                    'var_name': var_name,
                    'var_type': val_type,
                    'value_repr': val_repr,
                    'prev_value_repr': prev_val,
                    'is_changed': is_changed,
                    'scope_type': scope_type,
                    'meta': meta
                }
                all_vars.append(var_item)

                # Record delta if changed or if first time seen
                if is_changed or var_name not in self.previous_variables:
                    deltas.append(var_item)

            self.previous_variables = current_vars
            stdout_snapshot = self.captured_io.getvalue() if self.captured_io else ""

            self.db.record_step(
                exec_id=self.exec_id,
                step_id=self.step_count,
                line_no=line_no,
                code_line=code_line,
                func_name=frame.f_code.co_name,
                event_type=event,
                timestamp_us=timestamp_us,
                stack_depth=len(stack),
                stack_json=json.dumps(stack),
                deltas=deltas,
                stdout_snapshot=stdout_snapshot,
                all_vars=all_vars
            )

        return self._trace_dispatch

