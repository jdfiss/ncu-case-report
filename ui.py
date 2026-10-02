"""Drag-and-drop file upload UI for Case Report with one-click generation."""

import http.server
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

PORT = 8742
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

IGNORED = {"PUT_WEEKLY_FILES_HERE.txt"}

# Generation steps (matched against log output)
STEPS = [
    ("scan",     "掃描輸入資料",    ["extract_sources", "input/", "source_text", "掃描", "Step 1"]),
    ("casemap",  "建立 Case Map",   ["Case Map", "背景與時間線", "關鍵人物", "Step 2"]),
    ("issues",   "找出核心爭點",    ["爭點", "辯證", "張力", "Step 3"]),
    ("discuss",  "多元觀點討論",    ["觀點", "多元", "辯證", "Step 4"]),
    ("extend",   "延伸思考",        ["延伸", "理論框架", "反事實", "Step 5"]),
    ("synthesize","形成綜合觀點",   ["綜合觀點", "結論", "Step 6"]),
    ("write",    "撰寫正式報告",    ["case_report.md", "report_structure", "撰寫", "Step 7"]),
    ("review",   "自我審稿",        ["自評", "審稿", "quality_rubric", "Step 8"]),
    ("pdf",      "產生 PDF",        ["render_pdf", "case_report.pdf", "PDF", "Step 9"]),
]

# Generation state
gen_state = {
    "status": "idle",  # idle | running | done | error
    "logs": [],
    "started_at": None,
    "finished_at": None,
    "error": None,
    "step": -1,
}
gen_lock = threading.Lock()


def _find_claude():
    """Find the claude CLI executable."""
    # On Windows, subprocess needs the .cmd wrapper
    if os.name == "nt":
        cmd_path = shutil.which("claude.cmd") or shutil.which("claude")
    else:
        cmd_path = shutil.which("claude")
    return cmd_path


def run_generation():
    with gen_lock:
        gen_state["status"] = "running"
        gen_state["logs"] = ["Starting case report generation..."]
        gen_state["started_at"] = time.time()
        gen_state["finished_at"] = None
        gen_state["error"] = None
        gen_state["step"] = 0

    claude_bin = _find_claude()
    if not claude_bin:
        with gen_lock:
            gen_state["status"] = "error"
            gen_state["error"] = "claude CLI not found in PATH."
            gen_state["logs"].append(gen_state["error"])
            gen_state["finished_at"] = time.time()
        return

    with gen_lock:
        gen_state["logs"].append(f"Using: {claude_bin}")

    allowed = [
        "Bash", "Read", "Write", "Edit", "Glob", "Grep",
        "Skill", "WebSearch", "WebFetch",
    ]

    try:
        cmd = [
            claude_bin, "-p", "--verbose",
            "--allowedTools", " ".join(allowed),
        ]
        proc = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        proc.stdin.write("/case-report\n")
        proc.stdin.close()
        for line in proc.stdout:
            line = line.rstrip("\n\r")
            if line:
                with gen_lock:
                    gen_state["logs"].append(line)
                    if len(gen_state["logs"]) > 500:
                        gen_state["logs"] = gen_state["logs"][-300:]
                    cur = gen_state["step"]
                    for i in range(cur, len(STEPS)):
                        _, _, keywords = STEPS[i]
                        if any(kw in line for kw in keywords):
                            gen_state["step"] = i + 1
                            break

        proc.wait()

        with gen_lock:
            gen_state["finished_at"] = time.time()
            pdf_path = OUTPUT_DIR / "case_report.pdf"
            md_path = OUTPUT_DIR / "case_report.md"
            if proc.returncode == 0 and (pdf_path.exists() or md_path.exists()):
                gen_state["status"] = "done"
                gen_state["logs"].append("Report generation complete!")
            else:
                gen_state["status"] = "error"
                gen_state["error"] = f"Process exited with code {proc.returncode}"
                gen_state["logs"].append(f"Error: exit code {proc.returncode}")

    except FileNotFoundError:
        with gen_lock:
            gen_state["status"] = "error"
            gen_state["error"] = f"Could not execute: {claude_bin}"
            gen_state["logs"].append(gen_state["error"])
            gen_state["finished_at"] = time.time()
    except Exception as e:
        with gen_lock:
            gen_state["status"] = "error"
            gen_state["error"] = str(e)
            gen_state["logs"].append(f"Error: {e}")
            gen_state["finished_at"] = time.time()


HTML = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Case Report — 檔案管理</title>
<style>
  :root {
    --bg: #f8f9fa; --card: #fff; --border: #dee2e6;
    --text: #212529; --muted: #6c757d; --accent: #4361ee;
    --accent-hover: #3a50d9; --danger: #dc3545; --danger-hover: #c82333;
    --success: #198754; --drop-bg: #e8f0fe; --drop-border: #4361ee;
    --log-bg: #f1f3f5; --log-text: #495057;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #1a1a2e; --card: #16213e; --border: #374151;
      --text: #e2e8f0; --muted: #94a3b8; --accent: #818cf8;
      --accent-hover: #6366f1; --danger: #f87171; --danger-hover: #ef4444;
      --success: #34d399; --drop-bg: #1e293b; --drop-border: #818cf8;
      --log-bg: #0f172a; --log-text: #cbd5e1;
    }
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Segoe UI", "Microsoft JhengHei", system-ui, sans-serif;
    background: var(--bg); color: var(--text);
    min-height: 100vh; padding: 2rem;
  }
  .container { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 1.6rem; margin-bottom: .25rem; }
  .subtitle { color: var(--muted); margin-bottom: 1.5rem; font-size: .95rem; }

  .drop-zone {
    border: 2.5px dashed var(--border); border-radius: 16px;
    padding: 3rem 1.5rem; text-align: center;
    background: var(--card); cursor: pointer;
    transition: all .2s;
  }
  .drop-zone.over {
    border-color: var(--drop-border); background: var(--drop-bg);
    transform: scale(1.01);
  }
  .drop-zone .icon { font-size: 2.5rem; margin-bottom: .5rem; }
  .drop-zone p { color: var(--muted); }
  .drop-zone .formats { font-size: .8rem; color: var(--muted); margin-top: .5rem; }
  input[type=file] { display: none; }

  .section-title {
    font-size: 1.1rem; margin: 1.5rem 0 .75rem;
    display: flex; align-items: center; gap: .5rem;
  }
  .badge {
    background: var(--accent); color: #fff; font-size: .75rem;
    padding: .15rem .55rem; border-radius: 99px;
  }

  .file-list { list-style: none; }
  .file-item {
    display: flex; align-items: center; gap: .75rem;
    padding: .7rem 1rem; background: var(--card);
    border: 1px solid var(--border); border-radius: 10px;
    margin-bottom: .5rem; transition: background .15s;
  }
  .file-item:hover { background: var(--drop-bg); }
  .file-icon { font-size: 1.3rem; flex-shrink: 0; }
  .file-info { flex: 1; min-width: 0; }
  .file-name {
    font-weight: 500; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
  }
  .file-size { font-size: .8rem; color: var(--muted); }
  .btn-del {
    background: none; border: none; color: var(--danger);
    cursor: pointer; font-size: 1.1rem; padding: .25rem .5rem;
    border-radius: 6px; transition: background .15s;
  }
  .btn-del:hover { background: rgba(220,53,69,.12); }

  .empty-state {
    text-align: center; padding: 2rem; color: var(--muted);
    font-size: .95rem;
  }

  .actions {
    margin-top: 1.5rem; display: flex; gap: .75rem; flex-wrap: wrap;
    align-items: center;
  }
  .btn {
    padding: .6rem 1.4rem; border: none; border-radius: 10px;
    font-size: .95rem; font-weight: 500; cursor: pointer;
    transition: background .15s, transform .1s;
    display: inline-flex; align-items: center; gap: .5rem;
  }
  .btn:active { transform: scale(.97); }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover { background: var(--accent-hover); }
  .btn-primary:disabled {
    opacity: .55; cursor: not-allowed; transform: none;
  }
  .btn-outline {
    background: var(--card); color: var(--text);
    border: 1px solid var(--border);
  }
  .btn-outline:hover { background: var(--drop-bg); }
  .btn-success { background: var(--success); color: #fff; }
  .btn-success:hover { opacity: .9; }

  .toast {
    position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%);
    background: var(--success); color: #fff; padding: .6rem 1.2rem;
    border-radius: 10px; font-size: .9rem; opacity: 0;
    transition: opacity .3s; pointer-events: none; z-index: 99;
  }
  .toast.show { opacity: 1; }

  .progress-bar {
    width: 100%; height: 4px; background: var(--border);
    border-radius: 2px; margin-top: .5rem; overflow: hidden;
    display: none;
  }
  .progress-bar.active { display: block; }
  .progress-fill {
    height: 100%; background: var(--accent);
    border-radius: 2px; width: 0%; transition: width .3s;
  }

  /* Generation panel */
  .gen-panel {
    margin-top: 1.5rem; background: var(--card);
    border: 1px solid var(--border); border-radius: 12px;
    overflow: hidden; display: none;
  }
  .gen-panel.active { display: block; }
  .gen-header {
    padding: .75rem 1rem; display: flex; align-items: center;
    gap: .75rem; border-bottom: 1px solid var(--border);
  }
  .gen-status {
    font-weight: 600; font-size: .95rem;
    display: flex; align-items: center; gap: .5rem;
  }
  .gen-time { margin-left: auto; font-size: .8rem; color: var(--muted); }

  .spinner {
    width: 18px; height: 18px; border: 2.5px solid var(--border);
    border-top-color: var(--accent); border-radius: 50%;
    animation: spin .8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Step progress */
  .step-progress {
    padding: .75rem 1rem; border-bottom: 1px solid var(--border);
  }
  .step-bar-track {
    width: 100%; height: 8px; background: var(--border);
    border-radius: 4px; overflow: hidden; margin-bottom: .6rem;
  }
  .step-bar-fill {
    height: 100%; background: linear-gradient(90deg, var(--accent), var(--success));
    border-radius: 4px; width: 0%;
    transition: width .6s ease;
  }
  .step-labels {
    display: flex; flex-wrap: wrap; gap: .35rem;
  }
  .step-label {
    font-size: .72rem; padding: .2rem .5rem;
    border-radius: 6px; background: var(--border); color: var(--muted);
    transition: all .3s;
  }
  .step-label.done {
    background: var(--success); color: #fff;
  }
  .step-label.active {
    background: var(--accent); color: #fff;
    animation: pulse-step 1.5s ease infinite;
  }
  @keyframes pulse-step {
    0%, 100% { opacity: 1; }
    50% { opacity: .7; }
  }
  .step-pct {
    font-size: .8rem; font-weight: 600; color: var(--accent);
    text-align: right; margin-bottom: .3rem;
  }

  .gen-log {
    background: var(--log-bg); color: var(--log-text);
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: .8rem; line-height: 1.5;
    padding: .75rem 1rem; max-height: 220px;
    overflow-y: auto; white-space: pre-wrap;
    word-break: break-all;
  }
  .log-toggle {
    padding: .4rem 1rem; text-align: center;
    border-bottom: 1px solid var(--border);
  }
  .log-toggle button {
    background: none; border: none; color: var(--accent);
    cursor: pointer; font-size: .8rem;
  }
  .log-toggle button:hover { text-decoration: underline; }

  .output-section { margin-top: 1.5rem; }
  .output-card {
    display: flex; align-items: center; gap: .75rem;
    padding: .85rem 1rem; background: var(--card);
    border: 1px solid var(--success); border-radius: 10px;
    margin-bottom: .5rem;
  }
  .output-card .file-icon { color: var(--success); }
  .output-link {
    color: var(--accent); text-decoration: none; font-weight: 500;
  }
  .output-link:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="container">
  <h1>Case Report</h1>
  <p class="subtitle">拖曳檔案到下方區域，或點擊選取檔案，然後一鍵生成報告</p>

  <div class="drop-zone" id="dropZone">
    <div class="icon">📂</div>
    <p>拖曳檔案到這裡上傳</p>
    <p class="formats">PDF · DOCX · PPTX · TXT · MD · CSV · XLSX · 圖片</p>
    <div class="progress-bar" id="progress"><div class="progress-fill" id="progressFill"></div></div>
  </div>
  <input type="file" id="fileInput" multiple>

  <div class="section-title">
    已上傳檔案 <span class="badge" id="fileCount">0</span>
  </div>
  <ul class="file-list" id="fileList"></ul>
  <div class="empty-state" id="emptyState">尚無檔案，請拖曳或選取檔案上傳</div>

  <div class="actions">
    <button class="btn btn-primary" id="btnGenerate" onclick="generate()">
      <span id="btnGenIcon">&#9654;</span>
      <span id="btnGenText">一鍵生成報告</span>
    </button>
    <button class="btn btn-outline" onclick="clearAll()">清空全部</button>
  </div>

  <div class="gen-panel" id="genPanel">
    <div class="gen-header">
      <div class="gen-status" id="genStatus"></div>
      <div class="gen-time" id="genTime"></div>
    </div>
    <div class="step-progress" id="stepProgress">
      <div class="step-pct" id="stepPct">0%</div>
      <div class="step-bar-track"><div class="step-bar-fill" id="stepBarFill"></div></div>
      <div class="step-labels" id="stepLabels"></div>
    </div>
    <div class="log-toggle">
      <button onclick="toggleLog()">
        <span id="logToggleText">顯示詳細日誌 ▼</span>
      </button>
    </div>
    <div class="gen-log" id="genLog" style="display:none"></div>
  </div>

  <div class="output-section" id="outputSection" style="display:none">
    <div class="section-title">已產生報告</div>
    <div id="outputLinks"></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const fileCount = document.getElementById('fileCount');
const emptyState = document.getElementById('emptyState');
const progress = document.getElementById('progress');
const progressFill = document.getElementById('progressFill');
const btnGenerate = document.getElementById('btnGenerate');
const btnGenIcon = document.getElementById('btnGenIcon');
const btnGenText = document.getElementById('btnGenText');
const genPanel = document.getElementById('genPanel');
const genStatus = document.getElementById('genStatus');
const genTime = document.getElementById('genTime');
const genLog = document.getElementById('genLog');

let pollTimer = null;
let logVisible = false;

const EXT_ICONS = {
  pdf:'📄', docx:'📝', doc:'📝', pptx:'📊', ppt:'📊',
  txt:'📃', md:'📃', csv:'📈', xlsx:'📈', xls:'📈',
  png:'🖼️', jpg:'🖼️', jpeg:'🖼️', gif:'🖼️', webp:'🖼️', bmp:'🖼️',
};

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('over');
  uploadFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', () => {
  uploadFiles(fileInput.files);
  fileInput.value = '';
});

async function uploadFiles(files) {
  if (!files.length) return;
  progress.classList.add('active');
  let done = 0;
  for (const f of files) {
    const form = new FormData();
    form.append('file', f);
    await fetch('/upload', { method: 'POST', body: form });
    done++;
    progressFill.style.width = (done / files.length * 100) + '%';
  }
  setTimeout(() => {
    progress.classList.remove('active');
    progressFill.style.width = '0%';
  }, 500);
  toast(done + ' 個檔案上傳完成');
  loadFiles();
}

async function loadFiles() {
  const res = await fetch('/files');
  const files = await res.json();
  fileCount.textContent = files.length;
  if (!files.length) {
    fileList.innerHTML = '';
    emptyState.style.display = '';
    return;
  }
  emptyState.style.display = 'none';
  fileList.innerHTML = files.map(f => {
    const ext = f.name.split('.').pop().toLowerCase();
    const icon = EXT_ICONS[ext] || '📎';
    return `<li class="file-item">
      <span class="file-icon">${icon}</span>
      <div class="file-info">
        <div class="file-name" title="${esc(f.name)}">${esc(f.name)}</div>
        <div class="file-size">${fmtSize(f.size)}</div>
      </div>
      <button class="btn-del" title="刪除" onclick="del('${esc(f.name)}')">✕</button>
    </li>`;
  }).join('');
  loadOutputs();
}

async function loadOutputs() {
  const ores = await fetch('/outputs');
  const outs = await ores.json();
  const sec = document.getElementById('outputSection');
  const links = document.getElementById('outputLinks');
  if (outs.length) {
    sec.style.display = '';
    links.innerHTML = outs.map(o => {
      const icon = o.endsWith('.pdf') ? '📄' : '📝';
      return `<div class="output-card">
        <span class="file-icon">${icon}</span>
        <a class="output-link" href="/output/${encodeURIComponent(o)}" target="_blank">${esc(o)}</a>
      </div>`;
    }).join('');
  } else {
    sec.style.display = 'none';
  }
}

async function del(name) {
  await fetch('/delete?name=' + encodeURIComponent(name), { method: 'DELETE' });
  toast('已刪除 ' + name);
  loadFiles();
}

async function clearAll() {
  if (!confirm('確定要清空所有已上傳的檔案？')) return;
  await fetch('/clear', { method: 'DELETE' });
  toast('已清空全部檔案');
  loadFiles();
}

async function generate() {
  const fres = await fetch('/files');
  const files = await fres.json();
  if (!files.length) {
    toast('請先上傳檔案');
    return;
  }

  btnGenerate.disabled = true;
  btnGenIcon.innerHTML = '<span class="spinner" style="width:14px;height:14px;display:inline-block"></span>';
  btnGenText.textContent = '生成中...';
  genPanel.classList.add('active');
  genLog.textContent = '';
  genStatus.innerHTML = '<div class="spinner"></div> 正在生成報告...';
  genTime.textContent = '';

  await fetch('/generate', { method: 'POST' });
  startPolling();
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollStatus, 1500);
}

function toggleLog() {
  logVisible = !logVisible;
  genLog.style.display = logVisible ? '' : 'none';
  document.getElementById('logToggleText').textContent =
    logVisible ? '隱藏詳細日誌 ▲' : '顯示詳細日誌 ▼';
}

function updateSteps(step, total, labels, isDone) {
  const pct = isDone ? 100 : Math.round((step / total) * 100);
  document.getElementById('stepPct').textContent = pct + '%';
  document.getElementById('stepBarFill').style.width = pct + '%';

  const container = document.getElementById('stepLabels');
  if (labels && labels.length && container.children.length !== labels.length) {
    container.innerHTML = labels.map((l, i) =>
      `<span class="step-label" data-idx="${i}">${l}</span>`
    ).join('');
  }
  for (let i = 0; i < container.children.length; i++) {
    const el = container.children[i];
    el.className = 'step-label';
    if (isDone || i < step) el.classList.add('done');
    else if (i === step && !isDone) el.classList.add('active');
  }
}

async function pollStatus() {
  const res = await fetch('/gen-status');
  const s = await res.json();

  // update log
  genLog.textContent = s.logs.join('\n');
  genLog.scrollTop = genLog.scrollHeight;

  // update steps
  updateSteps(s.step || 0, s.total_steps || 9, s.step_labels, s.status === 'done');

  // update elapsed time
  if (s.started_at) {
    const end = s.finished_at || (Date.now() / 1000);
    const elapsed = Math.round(end - s.started_at);
    const mm = Math.floor(elapsed / 60);
    const ss = elapsed % 60;
    genTime.textContent = mm > 0 ? `${mm}m ${ss}s` : `${ss}s`;
  }

  if (s.status === 'done') {
    clearInterval(pollTimer);
    pollTimer = null;
    genStatus.innerHTML = '<span style="color:var(--success)">&#10003;</span> 報告生成完成！';
    btnGenerate.disabled = false;
    btnGenIcon.innerHTML = '&#9654;';
    btnGenText.textContent = '重新生成';
    toast('報告已生成完成！');
    loadOutputs();
  } else if (s.status === 'error') {
    clearInterval(pollTimer);
    pollTimer = null;
    genStatus.innerHTML = '<span style="color:var(--danger)">&#10007;</span> 生成失敗';
    updateSteps(s.step || 0, s.total_steps || 9, s.step_labels, false);
    btnGenerate.disabled = false;
    btnGenIcon.innerHTML = '&#9654;';
    btnGenText.textContent = '重試生成';
    // auto-show log on error
    if (!logVisible) toggleLog();
    toast('生成失敗，請查看日誌');
  }
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}
function fmtSize(b) {
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b/1024).toFixed(1) + ' KB';
  return (b/1048576).toFixed(1) + ' MB';
}
function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

// Initial load & check if already running
loadFiles();
fetch('/gen-status').then(r => r.json()).then(s => {
  if (s.status === 'running') {
    btnGenerate.disabled = true;
    btnGenIcon.innerHTML = '<span class="spinner" style="width:14px;height:14px;display:inline-block"></span>';
    btnGenText.textContent = '生成中...';
    genPanel.classList.add('active');
    genStatus.innerHTML = '<div class="spinner"></div> 正在生成報告...';
    startPolling();
  } else if (s.status === 'done' && s.logs.length) {
    genPanel.classList.add('active');
    genLog.textContent = s.logs.join('\n');
    genStatus.innerHTML = '<span style="color:var(--success)">&#10003;</span> 報告生成完成！';
    btnGenIcon.innerHTML = '&#9654;';
    btnGenText.textContent = '重新生成';
    if (s.started_at && s.finished_at) {
      const elapsed = Math.round(s.finished_at - s.started_at);
      const mm = Math.floor(elapsed / 60);
      const ss = elapsed % 60;
      genTime.textContent = mm > 0 ? `${mm}m ${ss}s` : `${ss}s`;
    }
  }
});
</script>
</body>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", ""):
            self._send(200, HTML, "text/html; charset=utf-8")

        elif parsed.path == "/files":
            files = []
            for f in sorted(INPUT_DIR.iterdir()):
                if f.is_file() and f.name not in IGNORED:
                    files.append({"name": f.name, "size": f.stat().st_size})
            self._send(200, json.dumps(files, ensure_ascii=False))

        elif parsed.path == "/outputs":
            outs = []
            if OUTPUT_DIR.exists():
                for f in sorted(OUTPUT_DIR.iterdir()):
                    if f.is_file():
                        outs.append(f.name)
            self._send(200, json.dumps(outs))

        elif parsed.path.startswith("/output/"):
            name = urllib.parse.unquote(parsed.path[len("/output/"):])
            fpath = OUTPUT_DIR / name
            if fpath.exists() and fpath.is_file():
                ct = "application/pdf" if name.endswith(".pdf") else "text/plain; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Disposition", f'inline; filename="{name}"')
                self.end_headers()
                self.wfile.write(fpath.read_bytes())
            else:
                self._send(404, '{"error":"not found"}')

        elif parsed.path == "/gen-status":
            with gen_lock:
                data = {
                    "status": gen_state["status"],
                    "logs": gen_state["logs"][-200:],
                    "started_at": gen_state["started_at"],
                    "finished_at": gen_state["finished_at"],
                    "error": gen_state["error"],
                    "step": gen_state["step"],
                    "total_steps": len(STEPS),
                    "step_labels": [s[1] for s in STEPS],
                }
            self._send(200, json.dumps(data, ensure_ascii=False))

        else:
            self._send(404, '{"error":"not found"}')

    def do_POST(self):
        if self.path == "/upload":
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self._send(400, '{"error":"bad content type"}')
                return
            boundary = content_type.split("boundary=")[1].encode()
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            filename, filedata = self._parse_multipart(body, boundary)
            if filename and filedata is not None:
                safe_name = Path(filename).name
                (INPUT_DIR / safe_name).write_bytes(filedata)
                self._send(200, json.dumps({"ok": True, "name": safe_name}))
            else:
                self._send(400, '{"error":"no file"}')

        elif self.path == "/generate":
            with gen_lock:
                if gen_state["status"] == "running":
                    self._send(409, '{"error":"already running"}')
                    return
            t = threading.Thread(target=run_generation, daemon=True)
            t.start()
            self._send(200, '{"ok":true}')

        else:
            self._send(404, '{"error":"not found"}')

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/delete":
            qs = urllib.parse.parse_qs(parsed.query)
            name = qs.get("name", [""])[0]
            fpath = INPUT_DIR / Path(name).name
            if fpath.exists():
                fpath.unlink()
            self._send(200, '{"ok":true}')
        elif parsed.path == "/clear":
            for f in INPUT_DIR.iterdir():
                if f.is_file() and f.name not in IGNORED:
                    f.unlink()
            self._send(200, '{"ok":true}')
        else:
            self._send(404, '{"error":"not found"}')

    def _parse_multipart(self, body, boundary):
        parts = body.split(b"--" + boundary)
        for part in parts:
            if b"Content-Disposition" not in part:
                continue
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            headers = part[:header_end].decode("utf-8", errors="replace")
            if 'name="file"' not in headers:
                continue
            fn_start = headers.find('filename="')
            if fn_start == -1:
                continue
            fn_start += len('filename="')
            fn_end = headers.find('"', fn_start)
            filename = headers[fn_start:fn_end]
            data = part[header_end + 4:]
            if data.endswith(b"\r\n"):
                data = data[:-2]
            return filename, data
        return None, None


def main():
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    server.socket.setsockopt(__import__("socket").SOL_SOCKET, __import__("socket").SO_REUSEADDR, 1)
    url = f"http://localhost:{PORT}"
    print(f"Case Report UI running at: {url}")
    print("Press Ctrl+C to stop.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
