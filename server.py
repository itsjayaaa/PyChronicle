"""
PyChronicle Standalone Python HTTP Web Server & Debugger API
100% Pure Python - No Node.js, TypeScript or External Dependencies Required.
Usage:
    python3 server.py [port]
"""

import sys
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Ensure local pychronicle module is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pychronicle.tracer import PyChronicleTracer
from pychronicle.ast_rewriter import analyze_ast
from pychronicle.graphs import SVGGraphGenerator
from pychronicle.main import run_tracer_json, SAMPLE_SCRIPTS

SAMPLE_CODES = {
    "bubble_sort": """# Bubble Sort Array Mutation
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
""",
    "fibonacci": """def generate_fib(n):
    sequence = [0, 1]
    for _ in range(n - 2):
        sequence.append(sequence[-1] + sequence[-2])
    return sequence

result = generate_fib(8)
print("Fibonacci Result:", result)
""",
    "binary_search": """def binary_search(arr, target):
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
""",
    "matrix_mutator": """matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]

for r in range(len(matrix)):
    for c in range(len(matrix[0])):
        if r == c:
            matrix[r][c] *= 10

print("Transformed Matrix:", matrix)
""",
    "prime_finder": """def find_primes(limit):
    primes = []
    for num in range(2, limit + 1):
        is_prime = True
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
    return primes

result = find_primes(20)
print("Primes found:", result)
"""
}


UI_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PyChronicle — Python Time-Travel Debugger</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; }
    pre, code, textarea, .font-mono { font-family: 'Fira Code', monospace; }
    .active-exec-line { background-color: rgba(56, 189, 248, 0.25) !important; border-left: 4px solid #38bdf8 !important; }
    .mutated-var { animation: highlight-pulse 1.2s ease-in-out; }
    @keyframes highlight-pulse {
      0% { background-color: rgba(74, 222, 128, 0.4); }
      100% { background-color: transparent; }
    }
  </style>
</head>
<body class="bg-[#090d13] text-[#e6edf3] h-screen flex flex-col overflow-hidden select-none">
  <!-- Top Navigation Bar -->
  <header class="bg-[#161b22] border-b border-[#30363d] px-4 py-2.5 flex items-center justify-between shrink-0 shadow-md">
    <div class="flex items-center gap-3">
      <div class="flex items-center gap-2 bg-[#21262d] px-2.5 py-1 rounded border border-[#30363d]">
        <span class="text-lg">⏳</span>
        <span class="font-bold text-sm tracking-tight text-white font-mono">PyChronicle</span>
      </div>

      <!-- Sample Selector Dropdown & File Upload -->
      <div class="flex items-center gap-2 text-xs">
        <label class="text-[#8b949e] font-medium hidden sm:inline">Algorithm:</label>
        <select id="sample-select" onchange="loadSampleScript()" class="bg-[#0d1117] border border-[#30363d] text-[#e6edf3] rounded px-2.5 py-1 text-xs focus:outline-none focus:border-[#38bdf8] font-mono cursor-pointer">
          <option value="bubble_sort">Bubble Sort Array Mutation</option>
          <option value="prime_finder" selected>Prime Number Finder (my_algorithm.py)</option>
          <option value="fibonacci">Fibonacci Sequence Generator</option>
          <option value="binary_search">Binary Search Step Tracker</option>
          <option value="matrix_mutator">2D Matrix Transformation</option>
        </select>

        <!-- Open / Upload Python File Button -->
        <label title="Open your local .py script" class="bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] border border-[#30363d] px-2.5 py-1 rounded text-xs font-mono cursor-pointer flex items-center gap-1">
          <span>📂</span> <span>Open .py</span>
          <input type="file" id="file-uploader" accept=".py,.txt" onchange="handleFileUpload(event)" class="hidden">
        </label>
      </div>

      <div class="flex items-center gap-1.5">
        <button onclick="executeTrace()" id="btn-trace" class="bg-[#238636] hover:bg-[#2ea043] text-white px-3 py-1 rounded text-xs font-semibold flex items-center gap-1.5 shadow transition-all cursor-pointer">
          <span>⚡</span> <span>Trace & Time-Travel</span>
        </button>
      </div>
    </div>

    <!-- Execution Metrics Badge & Top-Right Output -->
    <div id="metrics-bar" class="flex items-center gap-2.5 text-xs font-mono">
      <div class="bg-[#161b22] border border-[#30363d] px-2.5 py-1 rounded flex items-center gap-1.5 shrink-0">
        <span class="text-[#8b949e]">Status:</span>
        <span id="status-text" class="text-[#4ade80] font-semibold">READY</span>
      </div>
      <div class="bg-[#161b22] border border-[#30363d] px-2.5 py-1 rounded flex items-center gap-1.5 shrink-0">
        <span class="text-[#8b949e]">Execution:</span>
        <span id="metric-duration" class="text-[#fbbf24] font-semibold">0 ms</span>
      </div>
      <!-- Top Right Program Output Display -->
      <div id="stdout-badge" class="flex items-center gap-1.5 bg-[#15803d]/20 border border-[#22c55e]/50 px-3 py-1 rounded text-[#4ade80] font-mono shadow-sm max-w-[420px] shrink-0" title="Python Standard Output">
        <span class="text-[#8b949e] font-semibold flex items-center gap-1 shrink-0"><span>📟</span> Output:</span>
        <span id="stdout-text" class="font-bold text-[#4ade80] truncate">Ready to trace</span>
      </div>
    </div>
  </header>

  <!-- Main Split Layout -->
  <div class="flex-1 flex overflow-hidden">
    <!-- Left Column: Source Code Editor & Step Highlighter -->
    <div class="w-1/2 flex flex-col border-r border-[#30363d] bg-[#0d1117]">
      <div class="bg-[#161b22] px-3 py-1.5 border-b border-[#30363d] flex items-center justify-between text-xs font-semibold shrink-0">
        <div class="flex items-center gap-2">
          <span class="text-[#38bdf8] font-mono">🐍 Python Script Editor</span>
          <span class="text-[#8b949e] font-normal text-[11px]">(Live Tracing & Breakpoints)</span>
        </div>
        <div class="flex items-center gap-2">
          <button onclick="clearEditor()" title="Clear code editor" class="text-[11px] bg-[#21262d] hover:bg-[#30363d] text-[#8b949e] hover:text-white px-2 py-0.5 rounded font-mono border border-[#30363d] cursor-pointer">Clear</button>
          <span id="active-line-badge" class="text-[11px] bg-[#30363d] text-[#e6edf3] px-2 py-0.5 rounded font-mono">Line: --</span>
        </div>
      </div>

      <!-- Editor Body: Code View with Interactive Highlighting -->
      <div class="flex-1 flex overflow-hidden relative">
        <!-- Line Numbers Column -->
        <div id="line-numbers-col" class="w-10 bg-[#090d13] text-[#484f58] font-mono text-xs py-3 text-right pr-2 select-none border-r border-[#21262d] shrink-0">
          1
        </div>
        <!-- Editable Text Area -->
        <textarea id="code-editor" spellcheck="false" class="flex-1 bg-[#0d1117] text-[#e6edf3] p-3 font-mono text-xs leading-5 resize-none focus:outline-none overflow-auto whitespace-pre z-10" oninput="updateLineNumbers()"></textarea>
        <!-- Overlay for Highlighting Active Stepping Line -->
        <div id="code-highlight-overlay" class="absolute inset-y-0 left-10 right-0 pointer-events-none p-3 font-mono text-xs leading-5 whitespace-pre hidden"></div>
      </div>
    </div>

    <!-- Right Column: Time-Travel Playback, Inspector & Graphs -->
    <div class="w-1/2 flex flex-col bg-[#090d13] overflow-hidden">
      <!-- Time-Travel Scrubbing & Stepping Controls Bar -->
      <div class="bg-[#161b22] border-b border-[#30363d] p-3 flex flex-col gap-2.5 shrink-0 shadow-sm">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1.5">
            <button onclick="firstStep()" title="Jump to Start" class="p-1.5 bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] rounded border border-[#30363d] cursor-pointer text-xs">⏮ First</button>
            <button onclick="prevStep()" title="Step Backward" class="p-1.5 bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] rounded border border-[#30363d] cursor-pointer text-xs">◀ Step Back</button>
            <button onclick="togglePlay()" id="btn-play" title="Play / Pause Timeline" class="px-3 py-1.5 bg-[#1f6feb] hover:bg-[#388bfd] text-white rounded font-bold text-xs cursor-pointer flex items-center gap-1">▶ Play</button>
            <button onclick="nextStep()" title="Step Forward" class="p-1.5 bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] rounded border border-[#30363d] cursor-pointer text-xs">Step Next ▶</button>
            <button onclick="lastStep()" title="Jump to End" class="p-1.5 bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] rounded border border-[#30363d] cursor-pointer text-xs">Last ⏭</button>
          </div>

          <div class="flex items-center gap-3 text-xs font-mono">
            <div class="flex items-center gap-1.5">
              <span class="text-[#8b949e]">Speed:</span>
              <select id="playback-speed" class="bg-[#0d1117] border border-[#30363d] text-[#e6edf3] rounded px-1.5 py-0.5 text-xs">
                <option value="500">0.5x</option>
                <option value="250" selected>1.0x</option>
                <option value="100">2.5x</option>
                <option value="40">5.0x</option>
              </select>
            </div>
            <div class="bg-[#0d1117] border border-[#30363d] px-2.5 py-1 rounded text-xs flex items-center gap-1 font-mono shadow-inner">
              <span class="text-[#8b949e]">Step:</span>
              <span id="current-step-display" class="text-[#38bdf8] font-bold">0</span>
              <span class="text-[#6e7681]">/</span>
              <span id="total-steps-display" class="text-[#8b949e]">0</span>
            </div>
          </div>
        </div>

        <!-- Interactive Time-Travel Slider Bar -->
        <div class="flex items-center gap-3">
          <input type="range" id="step-slider" min="1" max="1" value="1" oninput="onSliderScrub(this.value)" class="w-full h-1.5 bg-[#21262d] rounded-lg appearance-none cursor-pointer accent-[#38bdf8]">
        </div>
      </div>

      <!-- Variable Inspector Table -->
      <div id="var-inspector-pane" class="h-48 flex flex-col bg-[#0d1117] shrink-0 overflow-hidden min-h-[100px]">
        <div class="bg-[#161b22] px-3 py-1.5 border-b border-[#30363d] flex items-center justify-between text-xs font-semibold shrink-0">
          <span class="text-[#fbbf24] flex items-center gap-1.5 font-mono">
            <span>🔍</span> Variable State Inspector & Scope
          </span>
          <span id="var-count-badge" class="text-[11px] text-[#8b949e] font-mono">0 variables active</span>
        </div>
        <div class="flex-1 overflow-auto">
          <table class="w-full text-left text-xs font-mono border-collapse">
            <thead class="bg-[#090d13] text-[#8b949e] text-[11px] sticky top-0 border-b border-[#21262d]">
              <tr>
                <th class="py-1 px-3 w-1/4">Name</th>
                <th class="py-1 px-3 w-1/6">Type</th>
                <th class="py-1 px-3 w-1/3">Value</th>
                <th class="py-1 px-3 w-1/6">Scope</th>
                <th class="py-1 px-3 text-right">Delta</th>
              </tr>
            </thead>
            <tbody id="variables-table-body" class="divide-y divide-[#21262d] text-[#e6edf3]">
              <tr>
                <td colspan="5" class="py-8 text-center text-[#6e7681]">No execution trace active. Click 'Trace & Time-Travel' to debug state.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Bottom Visualization Tabs (Timeline, Flow Map & Rich AST Tree) -->
      <div id="graphs-pane" class="flex-1 flex flex-col bg-[#0d1117] overflow-hidden min-h-[140px]">
        <div class="bg-[#161b22] border-b border-[#30363d] px-3 flex items-center justify-between shrink-0">
          <div class="flex items-center gap-1 text-xs">
            <button onclick="switchTab('graph-timeline')" id="tab-btn-timeline" class="px-3 py-1.5 border-b-2 border-[#38bdf8] text-[#38bdf8] font-bold cursor-pointer">
              📈 Variable Timeline Graph
            </button>
            <button onclick="switchTab('graph-heatmap')" id="tab-btn-heatmap" class="px-3 py-1.5 border-b-2 border-transparent text-[#8b949e] hover:text-[#e6edf3] font-bold cursor-pointer">
              📊 Execution Flow Map
            </button>
            <button onclick="switchTab('ast-inspector')" id="tab-btn-ast" class="px-3 py-1.5 border-b-2 border-transparent text-[#8b949e] hover:text-[#e6edf3] font-bold cursor-pointer flex items-center gap-1.5">
              <span>🌳</span> AST Syntax Tree
            </button>
          </div>
        </div>

        <div class="flex-1 p-2 overflow-auto flex items-center justify-center relative bg-[#090d13]">
          <div id="tab-timeline-container" class="w-full h-full flex items-center justify-center">
            <span class="text-[#6e7681] text-xs">Execute code to render live variable time-travel graph.</span>
          </div>

          <div id="tab-heatmap-container" class="w-full h-full flex items-center justify-center hidden">
            <span class="text-[#6e7681] text-xs">Execution flow map will generate upon execution.</span>
          </div>

          <!-- Rich Interactive AST Syntax Tree Container -->
          <div id="tab-ast-container" class="w-full h-full flex flex-col hidden bg-[#090d13] overflow-hidden">
            <!-- AST Sub-Header & Stats Badges -->
            <div class="flex items-center justify-between pb-2 border-b border-[#21262d] text-xs shrink-0 px-2 pt-1">
              <div class="flex items-center gap-2">
                <div class="flex items-center gap-1 bg-[#161b22] border border-[#30363d] rounded p-0.5">
                  <button onclick="setAstSubView('tree')" id="ast-subtab-tree" class="px-2 py-0.5 rounded text-[11px] font-semibold bg-[#38bdf8]/20 text-[#38bdf8] border border-[#38bdf8]/40">🌳 Tree View</button>
                  <button onclick="setAstSubView('summary')" id="ast-subtab-summary" class="px-2 py-0.5 rounded text-[11px] font-semibold text-[#8b949e] hover:text-white">📋 Summary</button>
                  <button onclick="setAstSubView('json')" id="ast-subtab-json" class="px-2 py-0.5 rounded text-[11px] font-semibold text-[#8b949e] hover:text-white">{ } JSON</button>
                </div>
              </div>
              <div id="ast-stats-badges" class="flex items-center gap-2 text-[11px] font-mono">
                <span class="text-[#8b949e]">AST ready</span>
              </div>
            </div>

            <!-- View 1: Visual Interactive Tree -->
            <div id="ast-view-tree" class="flex-1 overflow-auto p-2 font-mono text-xs select-text">
              <div class="text-[#6e7681] text-xs text-center py-6">No AST parsed yet. Click 'Trace & Time-Travel' to generate.</div>
            </div>

            <!-- View 2: Extracted Structural Summary -->
            <div id="ast-view-summary" class="flex-1 overflow-auto p-3 font-mono text-xs hidden space-y-3 select-text">
              <div id="ast-summary-content">No summary data.</div>
            </div>

            <!-- View 3: Formatted Raw JSON -->
            <div id="ast-view-json" class="flex-1 overflow-auto p-2 font-mono text-xs hidden select-text">
              <pre id="ast-json-view" class="text-[#38bdf8] text-[11px] leading-relaxed">No AST data loaded.</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Client-Side State Controller & Time-Travel Engine -->
  <script>
    const sampleScripts = {
      bubble_sort: `# Bubble Sort Array Mutation
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
`,
      fibonacci: `def generate_fib(n):
    sequence = [0, 1]
    for _ in range(n - 2):
        sequence.append(sequence[-1] + sequence[-2])
    return sequence

result = generate_fib(8)
print("Fibonacci Result:", result)
`,
      binary_search: `def binary_search(arr, target):
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
`,
      matrix_mutator: `matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]

for r in range(len(matrix)):
    for c in range(len(matrix[0])):
        if r == c:
            matrix[r][c] *= 10

print("Transformed Matrix:", matrix)
`,
      prime_finder: `def find_primes(limit):
    primes = []
    for num in range(2, limit + 1):
        is_prime = True
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
    return primes

result = find_primes(20)
print("Primes found:", result)
`
    };

    let traceData = null;
    let currentStepIndex = 1;
    let isPlaying = false;
    let playInterval = null;

    window.onload = () => {
      document.getElementById('code-editor').value = sampleScripts.prime_finder;
      updateLineNumbers();
      executeTrace();
    };

    function clearEditor() {
      document.getElementById('code-editor').value = '';
      updateLineNumbers();
      document.getElementById('code-editor').focus();
    }

    function handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target.result;
        document.getElementById('code-editor').value = content;
        updateLineNumbers();
        executeTrace();
      };
      reader.readAsText(file);
    }

    function loadSampleScript() {
      const key = document.getElementById('sample-select').value;
      if (sampleScripts[key]) {
        document.getElementById('code-editor').value = sampleScripts[key];
        updateLineNumbers();
        executeTrace();
      }
    }

    function updateLineNumbers() {
      const lines = document.getElementById('code-editor').value.split('\\n').length;
      let lineNums = '';
      for (let i = 1; i <= Math.max(lines, 1); i++) {
        lineNums += i + '\\n';
      }
      document.getElementById('line-numbers-col').innerText = lineNums;
    }

    async function executeTrace() {
      pauseTimeline();
      const code = document.getElementById('code-editor').value;
      const status = document.getElementById('status-text');
      status.innerText = 'TRACING...';
      status.className = 'text-[#38bdf8] font-semibold animate-pulse';

      try {
        const response = await fetch('/api/trace', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code })
        });
        const res = await response.json();

        if (res.error) {
          status.innerText = 'ERROR';
          status.className = 'text-[#f85149] font-semibold';
          alert('Trace Error: ' + res.error);
          return;
        }

        traceData = res;
        status.innerText = 'TRACED';
        status.className = 'text-[#4ade80] font-semibold';

        document.getElementById('metric-duration').innerText = (traceData.duration_ms || 0) + ' ms';
        document.getElementById('total-steps-display').innerText = traceData.total_steps;

        if (traceData.captured_stdout && traceData.captured_stdout.trim()) {
          const outStr = traceData.captured_stdout.trim();
          document.getElementById('stdout-text').innerText = outStr;
          document.getElementById('stdout-badge').title = outStr;
        } else {
          document.getElementById('stdout-text').innerText = '(No stdout output)';
          document.getElementById('stdout-badge').title = 'No standard output captured';
        }

        const slider = document.getElementById('step-slider');
        slider.min = 1;
        slider.max = traceData.total_steps;
        slider.value = 1;

        const timelineSvg = traceData.timeline_svg || traceData.svg_timeline;
        const heatmapSvg = traceData.heatmap_svg || traceData.svg_heatmap;
        const astData = traceData.ast_analysis || traceData.ast_json;

        if (timelineSvg) {
          document.getElementById('tab-timeline-container').innerHTML = timelineSvg;
        }
        if (heatmapSvg) {
          document.getElementById('tab-heatmap-container').innerHTML = heatmapSvg;
        }
        if (astData) {
          renderASTVisualizer(astData);
        }

        jumpToStep(1);
      } catch (err) {
        status.innerText = 'FAILED';
        status.className = 'text-[#f85149] font-semibold';
        console.error(err);
      }
    }

    function onSliderScrub(val) {
      jumpToStep(parseInt(val, 10));
    }

    function jumpToStep(stepId) {
      if (!traceData || !traceData.steps) return;
      stepId = Math.max(1, Math.min(stepId, traceData.total_steps));
      currentStepIndex = stepId;

      document.getElementById('step-slider').value = stepId;
      document.getElementById('current-step-display').innerText = stepId;

      const stepObj = traceData.steps[stepId - 1] || {};
      const activeLine = stepObj.line_number || 1;
      document.getElementById('active-line-badge').innerText = 'Line: ' + activeLine;

      highlightCodeLine(activeLine);

      // Render Variables Table
      const tbody = document.getElementById('variables-table-body');
      const allVars = stepObj.all_variables || [];
      document.getElementById('var-count-badge').innerText = allVars.length + ' variables active';

      if (allVars.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-[#6e7681]">No variables in current scope.</td></tr>';
      } else {
        let html = '';
        allVars.forEach(v => {
          const isChanged = v.is_changed;
          html += '<tr class="' + (isChanged ? 'bg-[#15803d]/20 text-white font-bold mutated-var' : 'hover:bg-[#161b22]') + '">'
            + '<td class="py-1 px-3 text-[#38bdf8] font-bold">' + escapeHtml(v.var_name) + '</td>'
            + '<td class="py-1 px-3 text-[#8b949e]">' + escapeHtml(v.var_type || 'any') + '</td>'
            + '<td class="py-1 px-3 font-mono ' + (isChanged ? 'text-[#4ade80]' : 'text-[#e6edf3]') + '">' + escapeHtml(v.value_repr || '') + '</td>'
            + '<td class="py-1 px-3 text-[#8b949e] text-[10px]">' + escapeHtml(v.scope_name || 'global') + '</td>'
            + '<td class="py-1 px-3 text-right">'
            + (isChanged ? '<span class="bg-[#238636] text-white text-[10px] px-1.5 py-0.5 rounded font-bold">MUTATED</span>' : '<span class="text-[#6e7681] text-[10px]">--</span>')
            + '</td></tr>';
        });
        tbody.innerHTML = html;
      }

      // Sync Top-Right Header Output Display
      const stdout = (stepObj.stdout_snapshot !== undefined && stepObj.stdout_snapshot !== '') 
        ? stepObj.stdout_snapshot 
        : (traceData.captured_stdout && traceData.captured_stdout.trim() ? traceData.captured_stdout.trim() : '');
      if (stdout) {
        document.getElementById('stdout-text').innerText = stdout;
        document.getElementById('stdout-badge').title = stdout;
      } else {
        document.getElementById('stdout-text').innerText = '(Pending stdout)';
      }

      // Update vertical step cursor line on SVG Timeline and Heatmap
      const cursorX = 60 + ((stepId - 1) / Math.max(traceData.total_steps - 1, 1)) * 710;
      const cursorTimeline = document.getElementById('svg-step-cursor-timeline');
      if (cursorTimeline) {
        cursorTimeline.setAttribute('x1', String(cursorX));
        cursorTimeline.setAttribute('x2', String(cursorX));
      }
      const cursorHeatmap = document.getElementById('svg-step-cursor-heatmap');
      if (cursorHeatmap) {
        cursorHeatmap.setAttribute('x1', String(cursorX));
        cursorHeatmap.setAttribute('x2', String(cursorX));
      }
    }

    function jumpToLineStep(lineNo) {
      if (!traceData || !traceData.steps) return;
      const targetStep = traceData.steps.find(s => s.line_number === lineNo);
      if (targetStep) {
        jumpToStep(targetStep.step_number);
      } else {
        highlightCodeLine(lineNo);
      }
    }

    function setAstSubView(subview) {
      document.getElementById('ast-subtab-tree').className = subview === 'tree' ? 'px-2 py-0.5 rounded text-[11px] font-semibold bg-[#38bdf8]/20 text-[#38bdf8] border border-[#38bdf8]/40' : 'px-2 py-0.5 rounded text-[11px] font-semibold text-[#8b949e] hover:text-white border border-transparent';
      document.getElementById('ast-subtab-summary').className = subview === 'summary' ? 'px-2 py-0.5 rounded text-[11px] font-semibold bg-[#38bdf8]/20 text-[#38bdf8] border border-[#38bdf8]/40' : 'px-2 py-0.5 rounded text-[11px] font-semibold text-[#8b949e] hover:text-white border border-transparent';
      document.getElementById('ast-subtab-json').className = subview === 'json' ? 'px-2 py-0.5 rounded text-[11px] font-semibold bg-[#38bdf8]/20 text-[#38bdf8] border border-[#38bdf8]/40' : 'px-2 py-0.5 rounded text-[11px] font-semibold text-[#8b949e] hover:text-white border border-transparent';

      document.getElementById('ast-view-tree').classList.toggle('hidden', subview !== 'tree');
      document.getElementById('ast-view-summary').classList.toggle('hidden', subview !== 'summary');
      document.getElementById('ast-view-json').classList.toggle('hidden', subview !== 'json');
    }

    function getNodeColorClass(type) {
      switch (type) {
        case 'Module': return 'bg-[#1f6feb]/20 text-[#58a6ff] border-[#1f6feb]/50';
        case 'FunctionDef': return 'bg-[#8957e5]/20 text-[#d2a8ff] border-[#8957e5]/50';
        case 'For':
        case 'While': return 'bg-[#d29922]/20 text-[#e3b341] border-[#d29922]/50';
        case 'If': return 'bg-[#e3b341]/20 text-[#f2cc60] border-[#e3b341]/50';
        case 'Assign':
        case 'AugAssign': return 'bg-[#238636]/20 text-[#7ee787] border-[#238636]/50';
        case 'Call': return 'bg-[#38bdf8]/20 text-[#7dd3fc] border-[#38bdf8]/50';
        case 'Compare':
        case 'BinOp': return 'bg-[#a371f7]/20 text-[#c9d1d9] border-[#8957e5]/40';
        case 'Name': return 'bg-[#21262d] text-[#38bdf8] border-[#30363d]';
        case 'Constant': return 'bg-[#21262d] text-[#a5d6ff] border-[#30363d]';
        case 'Return': return 'bg-[#f85149]/20 text-[#ff7b72] border-[#f85149]/50';
        default: return 'bg-[#161b22] text-[#c9d1d9] border-[#30363d]';
      }
    }

    function getNodeIcon(type) {
      switch (type) {
        case 'Module': return '📦';
        case 'FunctionDef': return '⚡';
        case 'For': return '🔄';
        case 'While': return '🔁';
        case 'If': return '🔀';
        case 'Assign': return '✏️';
        case 'AugAssign': return '➕=';
        case 'Call': return '📞';
        case 'Compare': return '⚖️';
        case 'BinOp': return '🧮';
        case 'Name': return '🏷️';
        case 'Constant': return '🔢';
        case 'Return': return '↩️';
        case 'Break': return '🛑';
        default: return '🔹';
      }
    }

    function renderASTVisualizer(astAnalysis) {
      document.getElementById('ast-json-view').innerText = JSON.stringify(astAnalysis, null, 2);

      const funcs = astAnalysis.functions || [];
      const loops = astAnalysis.loops || [];
      const assigns = astAnalysis.assignments || [];
      const vars = astAnalysis.variables || [];

      document.getElementById('ast-stats-badges').innerHTML = 
        '<span class="bg-[#8957e5]/20 text-[#d2a8ff] px-2 py-0.5 rounded border border-[#8957e5]/40">Fn: ' + funcs.length + '</span>' +
        '<span class="bg-[#d29922]/20 text-[#e3b341] px-2 py-0.5 rounded border border-[#d29922]/40">Loops: ' + loops.length + '</span>' +
        '<span class="bg-[#238636]/20 text-[#7ee787] px-2 py-0.5 rounded border border-[#238636]/40">Assign: ' + assigns.length + '</span>' +
        '<span class="bg-[#38bdf8]/20 text-[#38bdf8] px-2 py-0.5 rounded border border-[#38bdf8]/40">Vars: ' + vars.length + '</span>';

      let sumHtml = '';
      if (funcs.length > 0) {
        sumHtml += '<div class="bg-[#161b22] border border-[#30363d] p-2.5 rounded"><div class="text-[#d2a8ff] font-bold mb-1 flex items-center gap-1.5">⚡ Functions Declared (' + funcs.length + ')</div><ul class="space-y-1 text-xs">';
        funcs.forEach(f => {
          sumHtml += '<li class="flex items-center justify-between text-[#c9d1d9] bg-[#0d1117] px-2 py-1 rounded"><span><b class="text-[#79c0ff]">' + escapeHtml(f.name) + '</b>(' + f.args.join(', ') + ')</span><button onclick="jumpToLineStep(' + f.line + ')" class="text-[10px] bg-[#21262d] hover:bg-[#30363d] text-[#8b949e] px-1.5 py-0.5 rounded cursor-pointer">L:' + f.line + '</button></li>';
        });
        sumHtml += '</ul></div>';
      }
      if (loops.length > 0) {
        sumHtml += '<div class="bg-[#161b22] border border-[#30363d] p-2.5 rounded"><div class="text-[#e3b341] font-bold mb-1 flex items-center gap-1.5">🔄 Loop Constructs (' + loops.length + ')</div><ul class="space-y-1 text-xs">';
        loops.forEach(l => {
          sumHtml += '<li class="flex items-center justify-between text-[#c9d1d9] bg-[#0d1117] px-2 py-1 rounded"><span>target <b class="text-[#38bdf8]">' + escapeHtml(l.target) + '</b> in <code class="text-[#4ade80]">' + escapeHtml(l.iter) + '</code></span><button onclick="jumpToLineStep(' + l.line + ')" class="text-[10px] bg-[#21262d] hover:bg-[#30363d] text-[#8b949e] px-1.5 py-0.5 rounded cursor-pointer">L:' + l.line + '</button></li>';
        });
        sumHtml += '</ul></div>';
      }
      if (assigns.length > 0) {
        sumHtml += '<div class="bg-[#161b22] border border-[#30363d] p-2.5 rounded max-h-48 overflow-auto"><div class="text-[#7ee787] font-bold mb-1 flex items-center gap-1.5">✏️ State Assignments (' + assigns.length + ')</div><ul class="space-y-1 text-xs">';
        assigns.forEach(a => {
          sumHtml += '<li class="flex items-center justify-between text-[#c9d1d9] bg-[#0d1117] px-2 py-1 rounded"><span><b class="text-[#38bdf8]">' + escapeHtml(a.targets.join(', ')) + '</b> = <code class="text-[#a5d6ff]">' + escapeHtml(a.expr) + '</code></span><button onclick="jumpToLineStep(' + a.line + ')" class="text-[10px] bg-[#21262d] hover:bg-[#30363d] text-[#8b949e] px-1.5 py-0.5 rounded cursor-pointer">L:' + a.line + '</button></li>';
        });
        sumHtml += '</ul></div>';
      }
      document.getElementById('ast-summary-content').innerHTML = sumHtml || '<div class="text-[#6e7681] text-xs">No functions or loops identified.</div>';

      const treeRoot = astAnalysis.ast_tree || (astAnalysis.type ? astAnalysis : null);
      if (treeRoot) {
        document.getElementById('ast-view-tree').innerHTML = buildASTNodeDOM(treeRoot, 0);
      } else {
        document.getElementById('ast-view-tree').innerHTML = '<div class="text-[#6e7681]">AST Tree node object unavailable.</div>';
      }
    }

    function buildASTNodeDOM(node, depth) {
      if (!node || typeof node !== 'object') {
        return '<span class="text-[#a5d6ff]">' + escapeHtml(String(node)) + '</span>';
      }

      const nodeType = node.type || 'Node';
      const line = node.line;
      const fields = node.fields || {};
      const colorClass = getNodeColorClass(nodeType);
      const icon = getNodeIcon(nodeType);

      let lineBadge = '';
      if (line) {
        lineBadge = '<button onclick="jumpToLineStep(' + line + ')" title="Click to jump to line ' + line + '" class="ml-2 text-[10px] font-mono bg-[#21262d] hover:bg-[#30363d] text-[#38bdf8] px-1.5 py-0.5 rounded border border-[#30363d] cursor-pointer">L:' + line + '</button>';
      }

      let summaryInfo = '';
      if (nodeType === 'FunctionDef' && fields.name) {
        summaryInfo = '<span class="text-[#e6edf3] font-bold ml-1.5">' + escapeHtml(fields.name) + '()</span>';
      } else if (nodeType === 'Name' && fields.id) {
        summaryInfo = '<span class="text-[#79c0ff] font-bold ml-1.5">' + escapeHtml(fields.id) + '</span>';
      } else if (nodeType === 'Constant' && fields.value !== undefined) {
        summaryInfo = '<span class="text-[#a5d6ff] font-bold ml-1.5">' + escapeHtml(JSON.stringify(fields.value)) + '</span>';
      }

      const fieldKeys = Object.keys(fields).filter(k => k !== 'ctx');
      const hasChildren = fieldKeys.length > 0;
      const nodeId = 'ast-node-' + Math.random().toString(36).substr(2, 9);

      let html = '<div class="my-1 pl-2 border-l border-[#21262d]/60">';
      html += '<div class="flex items-center flex-wrap gap-1 text-xs py-0.5">';
      
      if (hasChildren) {
        html += '<button data-target="' + nodeId + '" onclick="toggleAstNode(this.dataset.target, this)" class="text-[#8b949e] hover:text-white font-mono px-1 py-0.5 text-[10px] bg-[#161b22] border border-[#30363d] rounded cursor-pointer select-none">▼</button>';
      }

      html += '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold border ' + colorClass + '"><span>' + icon + '</span> <span>' + escapeHtml(nodeType) + '</span></span>';
      html += summaryInfo;
      html += lineBadge;
      html += '</div>';

      if (hasChildren) {
        html += '<div id="' + nodeId + '" class="ml-3 pl-2 border-l border-[#30363d]/50 space-y-1 pt-0.5">';
        for (const key of fieldKeys) {
          const val = fields[key];
          if (Array.isArray(val)) {
            if (val.length === 0) continue;
            html += '<div class="text-[11px] text-[#8b949e] font-semibold mt-1"><span class="text-[#6e7681]">↳</span> ' + escapeHtml(key) + ' (' + val.length + '):</div>';
            val.forEach(child => {
              if (child && typeof child === 'object' && child.type) {
                html += buildASTNodeDOM(child, depth + 1);
              } else {
                html += '<div class="ml-3 text-[11px] text-[#c9d1d9]">' + escapeHtml(String(child)) + '</div>';
              }
            });
          } else if (val && typeof val === 'object' && val.type) {
            html += '<div class="text-[11px] text-[#8b949e] font-semibold mt-1"><span class="text-[#6e7681]">↳</span> ' + escapeHtml(key) + ':</div>';
            html += buildASTNodeDOM(val, depth + 1);
          } else if (val !== null && val !== undefined && key !== 'name' && key !== 'id' && key !== 'value') {
            html += '<div class="text-[11px] text-[#8b949e] ml-2"><span class="text-[#6e7681]">' + escapeHtml(key) + ':</span> <span class="text-[#c9d1d9]">' + escapeHtml(String(val)) + '</span></div>';
          }
        }
        html += '</div>';
      }

      html += '</div>';
      return html;
    }

    function toggleAstNode(nodeId, btn) {
      const el = document.getElementById(nodeId);
      if (!el) return;
      if (el.classList.contains('hidden')) {
        el.classList.remove('hidden');
        btn.innerText = '▼';
      } else {
        el.classList.add('hidden');
        btn.innerText = '▶';
      }
    }

    function prevStep() {
      if (currentStepIndex > 1) jumpToStep(currentStepIndex - 1);
    }
    function nextStep() {
      if (traceData && currentStepIndex < traceData.total_steps) jumpToStep(currentStepIndex + 1);
      else pauseTimeline();
    }
    function firstStep() { jumpToStep(1); }
    function lastStep() { if (traceData) jumpToStep(traceData.total_steps); }

    function togglePlay() {
      if (isPlaying) pauseTimeline();
      else playTimeline();
    }

    function playTimeline() {
      if (!traceData) return;
      if (currentStepIndex >= traceData.total_steps) currentStepIndex = 1;
      isPlaying = true;
      document.getElementById('btn-play').innerText = '⏸ Pause';
      document.getElementById('btn-play').className = 'px-3 py-1.5 bg-[#d29922] hover:bg-[#e3b341] text-black font-bold rounded text-xs cursor-pointer flex items-center gap-1';

      const speed = parseInt(document.getElementById('playback-speed').value, 10) || 250;
      playInterval = setInterval(() => {
        if (currentStepIndex < traceData.total_steps) {
          nextStep();
        } else {
          pauseTimeline();
        }
      }, speed);
    }

    function pauseTimeline() {
      isPlaying = false;
      if (playInterval) clearInterval(playInterval);
      playInterval = null;
      const btn = document.getElementById('btn-play');
      if (btn) {
        btn.innerText = '▶ Play';
        btn.className = 'px-3 py-1.5 bg-[#1f6feb] hover:bg-[#388bfd] text-white rounded font-bold text-xs cursor-pointer flex items-center gap-1';
      }
    }

    function highlightCodeLine(lineNum) {
      const code = document.getElementById('code-editor').value;
      const lines = code.split('\\n');
      let html = '';
      lines.forEach((line, idx) => {
        const lineIdx = idx + 1;
        const isActive = (lineIdx === lineNum);
        html += '<div class="' + (isActive ? 'active-exec-line text-[#38bdf8] font-bold' : 'text-transparent') + ' h-5 px-1">' + escapeHtml(line || ' ') + '</div>';
      });
      const overlay = document.getElementById('code-highlight-overlay');
      overlay.innerHTML = html;
      overlay.classList.remove('hidden');
    }

    function switchTab(tab) {
      document.getElementById('tab-btn-timeline').className = tab === 'graph-timeline' ? 'px-3 py-1.5 border-b-2 border-[#38bdf8] text-[#38bdf8] font-bold cursor-pointer' : 'px-3 py-1.5 border-b-2 border-transparent text-[#8b949e] hover:text-[#e6edf3] font-bold cursor-pointer';
      document.getElementById('tab-btn-heatmap').className = tab === 'graph-heatmap' ? 'px-3 py-1.5 border-b-2 border-[#38bdf8] text-[#38bdf8] font-bold cursor-pointer' : 'px-3 py-1.5 border-b-2 border-transparent text-[#8b949e] hover:text-[#e6edf3] font-bold cursor-pointer';
      document.getElementById('tab-btn-ast').className = tab === 'ast-inspector' ? 'px-3 py-1.5 border-b-2 border-[#38bdf8] text-[#38bdf8] font-bold cursor-pointer' : 'px-3 py-1.5 border-b-2 border-transparent text-[#8b949e] hover:text-[#e6edf3] font-bold cursor-pointer';

      document.getElementById('tab-timeline-container').classList.toggle('hidden', tab !== 'graph-timeline');
      document.getElementById('tab-heatmap-container').classList.toggle('hidden', tab !== 'graph-heatmap');
      document.getElementById('tab-ast-container').classList.toggle('hidden', tab !== 'ast-inspector');
    }

    function escapeHtml(str) {
      if (typeof str !== 'string') return String(str);
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
  </script>
</body>
</html>"""

class PyChronicleRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/sample/"):
            sample_key = path.replace("/api/sample/", "").strip()
            if sample_key in SAMPLE_CODES:
                self._send_json({"sample_key": sample_key, "code": SAMPLE_CODES[sample_key]})
            else:
                self._send_json({"error": f"Sample '{sample_key}' not found"}, status=404)
            return

        # Serve rich embedded UI directly from Python!
        content = UI_HTML_TEMPLATE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req_data = json.loads(post_body)
        except Exception:
            req_data = {}

        if path == "/api/trace":
            code = req_data.get("code")
            sample_key = req_data.get("sample_key")

            if not code and sample_key and sample_key in SAMPLE_CODES:
                code = SAMPLE_CODES[sample_key]
            elif not code:
                code = SAMPLE_CODES["bubble_sort"]

            trace_res = run_tracer_json(code, script_name="interactive.py")
            if not trace_res.get("success", False):
                self._send_json({"success": False, "error": trace_res.get("error", "Execution failed")}, status=400)
                return

            self._send_json(trace_res)
            return

        elif path == "/api/ast":
            code = req_data.get("code", "")
            analysis = analyze_ast(code)
            self._send_json(analysis)
            return

        self._send_json({"error": "Endpoint not found"}, status=404)


def run_server(port=3000):
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, PyChronicleRequestHandler)
    print(f"🐍 PyChronicle Pure-Python Server listening on http://0.0.0.0:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    run_server(port)
