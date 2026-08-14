"""
PyChronicle State Storage Engine (SQLite In-Memory/Disk)
Optimized schema for chronological variable deltas and time-travel querying.
"""

import sqlite3
import json
import time
from typing import Dict, Any, List, Optional, Tuple

class StateDatabase:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        with self.conn:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL,
                    script_name TEXT,
                    total_lines INTEGER,
                    total_steps INTEGER,
                    execution_time_ms REAL,
                    ast_json TEXT
                );

                CREATE TABLE IF NOT EXISTS steps (
                    step_id INTEGER PRIMARY KEY,
                    execution_id INTEGER,
                    line_number INTEGER,
                    code_line TEXT,
                    function_name TEXT,
                    event_type TEXT,
                    timestamp_us REAL,
                    stack_depth INTEGER,
                    stack_json TEXT,
                    stdout_snapshot TEXT,
                    all_vars_json TEXT,
                    FOREIGN KEY(execution_id) REFERENCES executions(id)
                );

                CREATE TABLE IF NOT EXISTS variable_deltas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_id INTEGER,
                    var_name TEXT,
                    var_type TEXT,
                    value_repr TEXT,
                    prev_value_repr TEXT,
                    is_changed INTEGER,
                    scope_type TEXT,
                    FOREIGN KEY(step_id) REFERENCES steps(step_id)
                );

                CREATE INDEX IF NOT EXISTS idx_steps_exec ON steps(execution_id);
                CREATE INDEX IF NOT EXISTS idx_deltas_step ON variable_deltas(step_id);
                CREATE INDEX IF NOT EXISTS idx_deltas_var ON variable_deltas(var_name);
            """)

    def create_execution(self, script_name: str, total_lines: int, ast_json: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO executions (created_at, script_name, total_lines, total_steps, execution_time_ms, ast_json)
            VALUES (?, ?, ?, 0, 0, ?)
        """, (time.time(), script_name, total_lines, ast_json))
        self.conn.commit()
        return cursor.lastrowid

    def record_step(self, exec_id: int, step_id: int, line_no: int, code_line: str,
                    func_name: str, event_type: str, timestamp_us: float,
                    stack_depth: int, stack_json: str,
                    deltas: List[Dict[str, Any]],
                    stdout_snapshot: str = "",
                    all_vars: Optional[List[Dict[str, Any]]] = None):
        cursor = self.conn.cursor()
        all_vars_json = json.dumps(all_vars or [])
        cursor.execute("""
            INSERT INTO steps (step_id, execution_id, line_number, code_line, function_name, event_type, timestamp_us, stack_depth, stack_json, stdout_snapshot, all_vars_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (step_id, exec_id, line_no, code_line, func_name, event_type, timestamp_us, stack_depth, stack_json, stdout_snapshot, all_vars_json))

        for d in deltas:
            cursor.execute("""
                INSERT INTO variable_deltas (step_id, var_name, var_type, value_repr, prev_value_repr, is_changed, scope_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (step_id, d['var_name'], d['var_type'], d['value_repr'], d.get('prev_value_repr'), 1 if d['is_changed'] else 0, d.get('scope_type', 'local')))

    def finalize_execution(self, exec_id: int, total_steps: int, exec_time_ms: float):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE executions SET total_steps = ?, execution_time_ms = ? WHERE id = ?
        """, (total_steps, exec_time_ms, exec_id))
        self.conn.commit()

    def get_execution_summary(self, exec_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM executions WHERE id = ?", (exec_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

    def get_all_steps(self, exec_id: int) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*,
                   (SELECT json_group_array(json_object(
                       'var_name', var_name,
                       'var_type', var_type,
                       'value_repr', value_repr,
                       'prev_value_repr', prev_value_repr,
                       'is_changed', is_changed,
                       'scope_type', scope_type
                   )) FROM variable_deltas WHERE step_id = s.step_id) as deltas_json
            FROM steps s
            WHERE s.execution_id = ?
            ORDER BY s.step_id ASC
        """, (exec_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['deltas'] = json.loads(d['deltas_json']) if d['deltas_json'] else []
            del d['deltas_json']
            d['all_variables'] = json.loads(d['all_vars_json']) if d.get('all_vars_json') else d['deltas']
            del d['all_vars_json']
            result.append(d)
        return result

    def reconstruct_state_at_step(self, exec_id: int, target_step_id: int) -> Dict[str, Any]:
        """
        Reconstructs exact variable state up to target_step_id by accumulating deltas.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM steps WHERE execution_id = ? AND step_id = ?", (exec_id, target_step_id))
        step_row = cursor.fetchone()
        if not step_row:
            return {}

        current_step = dict(step_row)

        cursor.execute("""
            SELECT vd.var_name, vd.var_type, vd.value_repr, vd.prev_value_repr, vd.step_id, vd.scope_type
            FROM variable_deltas vd
            JOIN steps s ON vd.step_id = s.step_id
            WHERE s.execution_id = ? AND s.step_id <= ?
            ORDER BY vd.id ASC
        """, (exec_id, target_step_id))

        deltas = cursor.fetchall()

        variables = {}
        changed_in_this_step = set()

        for d in deltas:
            v_name = d['var_name']
            variables[v_name] = {
                'var_name': v_name,
                'var_type': d['var_type'],
                'value_repr': d['value_repr'],
                'prev_value_repr': d['prev_value_repr'],
                'last_modified_step': d['step_id'],
                'scope_type': d['scope_type']
            }
            if d['step_id'] == target_step_id:
                changed_in_this_step.add(v_name)

        for v_name in variables:
            variables[v_name]['is_changed_now'] = (v_name in changed_in_this_step)

        return {
            'step': current_step,
            'variables': list(variables.values()),
            'stack': json.loads(current_step['stack_json']) if current_step['stack_json'] else []
        }

    def get_variable_timeline(self, exec_id: int, var_name: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT vd.step_id, s.line_number, s.code_line, vd.value_repr, vd.var_type, vd.prev_value_repr, s.timestamp_us
            FROM variable_deltas vd
            JOIN steps s ON vd.step_id = s.step_id
            WHERE s.execution_id = ? AND vd.var_name = ?
            ORDER BY vd.step_id ASC
        """, (exec_id, var_name))
        return [dict(r) for r in cursor.fetchall()]

    def close(self):
        self.conn.close()
