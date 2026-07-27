from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.containers import Vertical
from textual.events import Key


class PyChronicleUI(App):

    def __init__(self, steps, code):
        super().__init__()
        self.steps = steps
        self.code_lines = code.splitlines()
        self.index = 0

    def compose(self) -> ComposeResult:
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