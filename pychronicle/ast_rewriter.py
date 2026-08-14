"""
PyChronicle AST Rewriter & Visualizer
Parses target Python scripts using Python's ast module,
analyzes variable assignments, and transforms AST into inspectable trees.
"""

import ast
import json
from typing import Dict, Any, List, Optional

class ASTInspector(ast.NodeVisitor):
    def __init__(self):
        self.assignments: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.loops: List[Dict[str, Any]] = []
        self.variables_found: set = set()

    def visit_Assign(self, node: ast.Assign):
        targets = []
        for t in node.targets:
            if isinstance(t, ast.Name):
                targets.append(t.id)
                self.variables_found.add(t.id)
            elif isinstance(t, ast.Attribute):
                targets.append(f"{ast.unparse(t)}")
            elif isinstance(t, ast.Subscript):
                targets.append(f"{ast.unparse(t)}")
        
        self.assignments.append({
            'line': getattr(node, 'lineno', 0),
            'targets': targets,
            'expr': ast.unparse(node.value) if hasattr(node, 'value') else ''
        })
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign):
        target_name = ""
        if isinstance(node.target, ast.Name):
            target_name = node.target.id
            self.variables_found.add(node.target.id)
        else:
            target_name = ast.unparse(node.target)
            
        self.assignments.append({
            'line': getattr(node, 'lineno', 0),
            'targets': [target_name],
            'expr': ast.unparse(node)
        })
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        target_name = ""
        if isinstance(node.target, ast.Name):
            target_name = node.target.id
            self.variables_found.add(node.target.id)
        else:
            target_name = ast.unparse(node.target)
            
        self.loops.append({
            'line': getattr(node, 'lineno', 0),
            'target': target_name,
            'iter': ast.unparse(node.iter)
        })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        args = [a.arg for a in node.args.args]
        self.functions.append({
            'name': node.name,
            'line': getattr(node, 'lineno', 0),
            'args': args
        })
        self.generic_visit(node)


def ast_to_dict(node: ast.AST) -> Dict[str, Any]:
    """Recursively converts an AST node into a clean JSON serializable dictionary for UI visualization."""
    node_type = node.__class__.__name__
    res: Dict[str, Any] = {
        "type": node_type,
        "line": getattr(node, "lineno", None)
    }

    fields = {}
    for field, value in ast.iter_fields(node):
        if isinstance(value, ast.AST):
            fields[field] = ast_to_dict(value)
        elif isinstance(value, list):
            fields[field] = [ast_to_dict(item) if isinstance(item, ast.AST) else str(item) for item in value]
        elif isinstance(value, (str, int, float, bool, type(None))):
            fields[field] = value
        else:
            fields[field] = str(value)

    res["fields"] = fields
    return res


def analyze_ast(source_code: str) -> Dict[str, Any]:
    """Parses source code and extracts AST analysis metadata."""
    try:
        tree = ast.parse(source_code)
        inspector = ASTInspector()
        inspector.visit(tree)
        tree_dict = ast_to_dict(tree)

        return {
            "success": True,
            "assignments": inspector.assignments,
            "functions": inspector.functions,
            "loops": inspector.loops,
            "variables": list(inspector.variables_found),
            "ast_tree": tree_dict,
            "unparsed": ast.unparse(tree)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
