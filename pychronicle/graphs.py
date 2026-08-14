"""
PyChronicle Graph Visualization Engine
Generates SVG graphs for variable state changes over execution steps,
execution heatmaps, and mutation frequencies.
"""

from typing import List, Dict, Any, Optional
import math

class SVGGraphGenerator:
    @staticmethod
    def generate_variable_timeline_svg(
        steps: List[Dict[str, Any]],
        var_timelines: Dict[str, List[Dict[str, Any]]],
        watched_vars: List[str],
        width: int = 800,
        height: int = 280
    ) -> str:
        """Generates an SVG line graph showing variable value changes over step index."""
        if not steps or not watched_vars:
            return f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" class="w-full">
                <rect width="100%" height="100%" fill="#0d1117" rx="8"/>
                <text x="50%" y="50%" fill="#6e7681" font-family="monospace" font-size="14" text-anchor="middle">No variable timeline data available</text>
            </svg>"""

        margin_left = 60
        margin_right = 30
        margin_top = 40
        margin_bottom = 50
        chart_w = width - margin_left - margin_right
        chart_h = height - margin_top - margin_bottom

        total_steps = max(len(steps), 1)

        # Parse numerical values or collection lengths for plotting
        parsed_data = {}  # var_name -> list of (step_id, float_val, orig_repr)
        all_numeric_vals = []

        colors = ["#38bdf8", "#4ade80", "#f43f5e", "#fbbf24", "#c084fc", "#f472b6", "#a3e635"]

        for idx, var in enumerate(watched_vars):
            timeline = var_timelines.get(var, [])
            var_data = []
            for item in timeline:
                val_str = item["value_repr"].strip('"\'')
                # Try parsing as float/int, or list/dict length
                parsed_val = None
                try:
                    if val_str.startswith("[") or val_str.startswith("(") or val_str.startswith("{"):
                        # Count elements or evaluate
                        parsed_val = val_str.count(",") + 1 if len(val_str) > 2 else 0
                    else:
                        parsed_val = float(val_str)
                except ValueError:
                    parsed_val = len(val_str)  # fallback to string length

                if parsed_val is not None:
                    var_data.append((item["step_id"], parsed_val, item["value_repr"]))
                    all_numeric_vals.append(parsed_val)

            parsed_data[var] = var_data

        min_val = min(all_numeric_vals) if all_numeric_vals else 0
        max_val = max(all_numeric_vals) if all_numeric_vals else 10
        if min_val == max_val:
            min_val -= 1
            max_val += 1

        val_range = max_val - min_val

        # SVG header
        svg = [f'<svg id="timeline-svg-chart" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" class="w-full h-full block select-none" style="min-height: 180px;">']
        svg.append('<rect width="100%" height="100%" fill="#0d1117" rx="8" stroke="#30363d" stroke-width="1"/>')

        # Title
        svg.append(f'<text x="{margin_left}" y="24" fill="#e6edf3" font-family="monospace" font-size="13" font-weight="bold">📈 Variable Value Timeline Graph</text>')

        # Grid lines & Y-axis labels
        num_y_ticks = 4
        for i in range(num_y_ticks + 1):
            y_ratio = i / num_y_ticks
            y_pos = margin_top + chart_h - (y_ratio * chart_h)
            val_tick = min_val + (y_ratio * val_range)

            svg.append(f'<line x1="{margin_left}" y1="{y_pos}" x2="{width - margin_right}" y2="{y_pos}" stroke="#21262d" stroke-width="1" stroke-dasharray="3,3"/>')
            svg.append(f'<text x="{margin_left - 8}" y="{y_pos + 4}" fill="#8b949e" font-family="monospace" font-size="10" text-anchor="end">{round(val_tick, 1)}</text>')

        # X-axis
        svg.append(f'<line x1="{margin_left}" y1="{margin_top + chart_h}" x2="{width - margin_right}" y2="{margin_top + chart_h}" stroke="#30363d" stroke-width="1.5"/>')
        svg.append(f'<text x="{width / 2}" y="{height - 10}" fill="#8b949e" font-family="monospace" font-size="11" text-anchor="middle">Execution Step →</text>')

        # Plot variables
        legend_x = margin_left + 220
        for idx, var in enumerate(watched_vars):
            color = colors[idx % len(colors)]
            data = parsed_data.get(var, [])

            # Draw Legend
            lx = legend_x + (idx * 110)
            if lx + 100 < width - margin_right:
                svg.append(f'<rect x="{lx}" y="12" width="10" height="10" fill="{color}" rx="2"/>')
                svg.append(f'<text x="{lx + 14}" y="21" fill="#e6edf3" font-family="monospace" font-size="11">{var}</text>')

            if not data:
                continue

            points = []
            for step_id, val, orig_repr in data:
                x_pos = margin_left + ((step_id - 1) / max(total_steps - 1, 1)) * chart_w
                y_pos = margin_top + chart_h - (((val - min_val) / val_range) * chart_h)
                points.append((x_pos, y_pos, step_id, val, orig_repr))

            # Draw polyline
            if len(points) > 1:
                pts_str = " ".join([f"{p[0]:.1f},{p[1]:.1f}" for p in points])
                svg.append(f'<polyline points="{pts_str}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')

            # Draw circles & tooltips with interactive click handler
            for x, y, step_id, val, orig_repr in points:
                clean_repr = orig_repr.replace('"', '&quot;').replace("'", "&#039;")
                svg.append(f'''
                    <circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}" stroke="#0d1117" stroke-width="1.5" 
                            class="cursor-pointer hover:r-6 hover:fill-[#fbbf24] transition-all"
                            onclick="jumpToStep({step_id})"
                            style="cursor: pointer;">
                        <title>Click to jump to Step {step_id}: {var} = {clean_repr}</title>
                    </circle>
                ''')

        # Dynamic vertical active step cursor line
        initial_x = margin_left
        svg.append(f'<line id="svg-step-cursor-timeline" x1="{initial_x}" y1="{margin_top}" x2="{initial_x}" y2="{margin_top + chart_h}" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4,4" opacity="0.95"/>')

        svg.append('</svg>')
        return "".join(svg)


    @staticmethod
    def generate_execution_flow_heatmap_svg(
        steps: List[Dict[str, Any]],
        total_lines: int,
        width: int = 800,
        height: int = 240
    ) -> str:
        """Generates a line execution flow heatmap over time."""
        if not steps:
            return f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" class="w-full">
                <rect width="100%" height="100%" fill="#0d1117" rx="8"/>
                <text x="50%" y="50%" fill="#6e7681" font-family="monospace" font-size="14" text-anchor="middle">No execution steps</text>
            </svg>"""

        margin_left = 60
        margin_right = 30
        margin_top = 40
        margin_bottom = 45
        chart_w = width - margin_left - margin_right
        chart_h = height - margin_top - margin_bottom

        max_lines = max(total_lines, 1)
        total_steps = max(len(steps), 1)

        svg = [f'<svg id="heatmap-svg-chart" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" class="w-full h-full block select-none" style="min-height: 180px;">']
        svg.append('<rect width="100%" height="100%" fill="#0d1117" rx="8" stroke="#30363d" stroke-width="1"/>')
        svg.append(f'<text x="{margin_left}" y="24" fill="#e6edf3" font-family="monospace" font-size="13" font-weight="bold">📊 Execution Flow & Line Map (Step vs Line)</text>')

        # Y-axis (Line Numbers)
        svg.append(f'<text x="{margin_left - 8}" y="{margin_top + 10}" fill="#8b949e" font-family="monospace" font-size="10" text-anchor="end">Line 1</text>')
        svg.append(f'<text x="{margin_left - 8}" y="{margin_top + chart_h}" fill="#8b949e" font-family="monospace" font-size="10" text-anchor="end">Line {max_lines}</text>')

        # Trace points
        points = []
        for s in steps:
            step_id = s["step_id"]
            line_no = s["line_number"]
            x = margin_left + ((step_id - 1) / max(total_steps - 1, 1)) * chart_w
            y = margin_top + ((line_no - 1) / max(max_lines - 1, 1)) * chart_h
            points.append((x, y, step_id, line_no, s["code_line"]))

        if len(points) > 1:
            pts_str = " ".join([f"{p[0]:.1f},{p[1]:.1f}" for p in points])
            svg.append(f'<polyline points="{pts_str}" fill="none" stroke="#38bdf8" stroke-width="1.5" stroke-opacity="0.6"/>')

        for x, y, step_id, line_no, code in points:
            clean_code = code.replace('"', '&quot;').replace("'", "&#039;")
            svg.append(f'''
                <circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#4ade80" stroke="#0d1117" stroke-width="1"
                        class="cursor-pointer hover:r-6 hover:fill-[#fbbf24] transition-all"
                        onclick="jumpToStep({step_id})"
                        style="cursor: pointer;">
                    <title>Click to jump to Step {step_id} | Line {line_no}: {clean_code}</title>
                </circle>
            ''')

        # Dynamic vertical active step cursor line
        initial_x = margin_left
        svg.append(f'<line id="svg-step-cursor-heatmap" x1="{initial_x}" y1="{margin_top}" x2="{initial_x}" y2="{margin_top + chart_h}" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4,4" opacity="0.95"/>')

        # X Axis
        svg.append(f'<line x1="{margin_left}" y1="{margin_top + chart_h}" x2="{width - margin_right}" y2="{margin_top + chart_h}" stroke="#30363d" stroke-width="1.5"/>')
        svg.append(f'<text x="{width / 2}" y="{height - 10}" fill="#8b949e" font-family="monospace" font-size="11" text-anchor="middle">Execution Timeline Steps (1 to {total_steps}) →</text>')

        svg.append('</svg>')
        return "".join(svg)
