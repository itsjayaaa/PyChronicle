import ast

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