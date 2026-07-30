try:
    # Import Textual types when available
    from textual.app import App, ComposeResult  # type: ignore[reportMissingImports]
    from textual.widgets import Static  # type: ignore[reportMissingImports]
    from textual.containers import Vertical  # type: ignore[reportMissingImports]
    from textual.events import Key  # type: ignore[reportMissingImports]
except Exception:  # Fallback stubs for editors/linters when textual is not installed
    from typing import Any

    ComposeResult = Any

    class App:  # minimal stub
        def __init__(self, *args, **kwargs):
            # Minimal runtime state for the stubbed App
            self._exited = False
            self._mounted = False

        def run(self):
            """Run a minimal stubbed app.

            This will attempt to call compose() to create widgets and on_mount()
            to initialize state. It won't start an event loop; it simply
            performs the minimal steps necessary so code depending on those
            methods can operate when Textual isn't installed.
            """
            # Attempt to compose UI elements if present
            compose = getattr(self, "compose", None)
            if callable(compose):
                try:
                    # consume generator if ComposeResult is a generator
                    result = compose()
                    # If result is a generator, exhaust it to trigger any side-effects
                    if hasattr(result, "__iter__"):
                        list(result)
                except Exception:
                    # Best-effort: ignore compose errors in stub
                    pass

            # Call on_mount if implemented
            on_mount = getattr(self, "on_mount", None)
            if callable(on_mount):
                try:
                    on_mount()
                    self._mounted = True
                except Exception:
                    # ignore errors in stub
                    pass

            return

        def exit(self):
            """Mark the stubbed app as exited.

            Code using the stub can check the _exited attribute to know if an
            exit was requested.
            """
            self._exited = True

    class Static:  # minimal stub used for update()
        def __init__(self, *args, **kwargs):
            self._text = ""

        def update(self, text: str):
            self._text = text

    class Vertical(tuple):
        pass

    class Key:  # event stub
        def __init__(self, key: str):
            self.key = key


class PyChronicleUI(App):

    def __init__(self, steps, code):
        super().__init__()
        # Ensure we always have at least one step to display
        self.steps = steps if steps else [{"line": 1, "vars": {}, "output": ""}]
        self.code_lines = code.splitlines()
        self.index = 0

    def compose(self):
        self.header = Static()
        self.code_view = Static()
        self.bottom_panel = Static()

        yield Vertical(
            self.header,
            self.code_view,
            self.bottom_panel
        )

    def on_mount(self):
        self.update_view()

    def update_view(self):
        # Protect against inconsistent index
        if not self.steps:
            self.index = 0
            return
        if self.index >= len(self.steps):
            self.index = len(self.steps) - 1

        step = self.steps[self.index]

        # 🔥 HEADER
        self.header.update(
            f"[bold yellow]🔥 PyChronicle Time Travel Debugger[/bold yellow]\n"
            f"[white]Step {self.index+1}/{len(self.steps)} | Line {step['line']}[/white]\n"
            f"[cyan]⬅️ Left | ➡️ Right | q Quit[/cyan]"
        )

        # 🔥 CODE WITH HIGHLIGHT
        code_display = ""
        for i, line in enumerate(self.code_lines, start=1):
            if i == step["line"]:
                code_display += f"[black on yellow]> {i}: {line}[/]\n"
            else:
                code_display += f"  {i}: {line}\n"

        self.code_view.update(code_display)

        # 🔥 VARIABLES
        vars_text = "\n".join(
            f"{k} = {v}" for k, v in step["vars"].items()
        )

        # 🔥 OUTPUT (FULL OUTPUT FROM TRACER)
        output_text = step.get("output", "")

        # 🔥 BOTTOM PANEL
        self.bottom_panel.update(
            f"[bold green]Variables:[/bold green]\n{vars_text if vars_text else 'None'}\n\n"
            f"[bold magenta]Output:[/bold magenta]\n{output_text if output_text else 'No output yet'}"
        )

    # 🔥 KEY CONTROLS
    def on_key(self, event: Key):
        if event.key == "right":
            if self.index < len(self.steps) - 1:
                self.index += 1
                self.update_view()

        elif event.key == "left":
            if self.index > 0:
                self.index -= 1
                self.update_view()

        elif event.key == "q":
            self.exit()


# 🔥 RUN FUNCTION (IMPORTANT)
def run_ui(steps, code):
    app = PyChronicleUI(steps, code)
    app.run()


if __name__ == "__main__":
    # Minimal demo when run as a script
    sample_code = """for i in range(3):
    print(i)
"""
    sample_steps = [
        {"line": 1, "vars": {"i": 0}, "output": ""},
        {"line": 2, "vars": {"i": 0}, "output": "0\n"},
        {"line": 1, "vars": {"i": 1}, "output": "0\n"},
        {"line": 2, "vars": {"i": 1}, "output": "0\n1\n"},
        {"line": 1, "vars": {"i": 2}, "output": "0\n1\n"},
        {"line": 2, "vars": {"i": 2}, "output": "0\n1\n2\n"},
    ]
    run_ui(sample_steps, sample_code)