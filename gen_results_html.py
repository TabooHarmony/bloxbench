import json, base64, re
from pathlib import Path
from html import escape

# Local operator artifact directory. Keep run output out of git.
results_dir = Path(__file__).parent / "results_pull"

# Auto-discover all run dirs (sorted newest first by mtime)
RUN_DIRS = sorted(
    [d for d in results_dir.iterdir() if d.is_dir() and (d / "results.json").exists()],
    key=lambda d: d.stat().st_mtime,
    reverse=True,
)

def load_run(run_dir):
    data = json.load(open(run_dir / "results.json"))
    shots = {}
    ss_dir = run_dir / "screenshots"
    if ss_dir.exists():
        for f in ss_dir.glob("*.png"):
            b64 = base64.b64encode(f.read_bytes()).decode("ascii")
            shots[f.name] = f"data:image/png;base64,{b64}"
    return data, shots

# Load all runs
ALL_RUNS = {}
for rd in RUN_DIRS:
    data, shots = load_run(rd)
    ALL_RUNS[rd.name] = {"data": data, "shots": shots, "dir": rd}

# Default comparison: first two runs (most recent)
run_names = list(ALL_RUNS.keys())
LEFT_RUN = run_names[0] if len(run_names) > 0 else ""
RIGHT_RUN = run_names[1] if len(run_names) > 1 else (run_names[0] if run_names else "")

left = ALL_RUNS.get(LEFT_RUN, {"data": {"evals": [], "summary": {}}, "shots": {}})
right = ALL_RUNS.get(RIGHT_RUN, {"data": {"evals": [], "summary": {}}, "shots": {}})

left_evals = {e["scenario"]: e for e in left["data"].get("evals", [])}
right_evals = {e["scenario"]: e for e in right["data"].get("evals", [])}
all_scenarios = sorted(set(list(left_evals.keys()) + list(right_evals.keys())))

# Extract eval prompts from Lua files
EVAL_PROMPTS = {}
for f in sorted(Path("/root/bloxbench/Evals").rglob("*.lua")):
    content = f.read_text()
    name_m = re.search(r'scenario_name\s*=\s*"([^"]+)"', content)
    prompt_m = re.search(r'content\s*=\s*\[\[(.+?)\]\]', content, re.DOTALL)
    if name_m and prompt_m:
        EVAL_PROMPTS[name_m.group(1)] = prompt_m.group(1).strip()

def fmt_tokens(v):
    if v is None: return "—"
    return f"{v:,}"
def fmt_time(v):
    if v is None: return "—"
    return f"{v/1000:.0f}s"

css = """<style>
:root{--bg:#1e1e2e;--bg-alt:#181825;--bg-card:#313244;--bg-hover:#45475a;--text:#cdd6f4;--text-dim:#a6adc8;--text-muted:#6c7086;--accent:#89b4fa;--accent2:#f9e2af;--green:#a6e3a1;--red:#f38ba8;--yellow:#f9e2af;--mauve:#cba6f7;--blue:#89b4fa}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:monospace;font-size:13px;line-height:1.5;padding:20px}
h1{color:var(--accent);margin-bottom:4px;font-size:20px}
.subtitle{color:var(--text-dim);margin-bottom:16px;font-size:12px}
.run-selector{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;align-items:center}
.summary{display:flex;gap:20px;margin-bottom:24px;flex-wrap:wrap}
.summary-card{background:var(--bg-card);padding:16px;border-radius:8px;flex:1;min-width:280px}
.summary-card h3{margin-bottom:8px;font-size:14px}
.summary-card.left h3{color:var(--mauve)}
.summary-card.right h3{color:var(--blue)}
.metric{display:flex;justify-content:space-between;padding:2px 0}
.metric-label{color:var(--text-dim)}
.metric-value{color:var(--text);font-weight:bold}
.nav{display:flex;gap:4px;margin-bottom:20px;flex-wrap:wrap}
.nav-item{background:var(--bg-card);padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;text-decoration:none;color:var(--text);transition:background .2s}
.nav-item:hover{background:var(--bg-hover)}
.eval-section{background:var(--bg-alt);padding:20px;border-radius:8px;margin-bottom:24px}
.eval-header{display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap}
.eval-name{color:var(--accent2);font-size:16px;font-weight:bold}
.eval-prompt{background:var(--bg);padding:10px 14px;border-radius:6px;margin-bottom:16px;font-size:12px;color:var(--text-dim);border-left:3px solid var(--accent);white-space:pre-wrap;line-height:1.6}
.comparison{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.side{background:var(--bg-card);padding:16px;border-radius:8px}
.side.left{border-top:3px solid var(--mauve)}
.side.right{border-top:3px solid var(--blue)}
.side h3{margin-bottom:8px;font-size:13px}
.side.left h3{color:var(--mauve)}
.side.right h3{color:var(--blue)}
.metrics-grid{display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;margin-bottom:12px}
.mp{display:flex;justify-content:space-between;font-size:12px}
.mp .l{color:var(--text-muted)}
.mp .v{color:var(--text)}
.screenshots{margin:12px 0}
.screenshots label{color:var(--text-dim);font-size:11px;display:block;margin-bottom:4px}
.ss-row{display:flex;gap:8px;flex-wrap:wrap}
.ss-row img{width:200px;height:auto;border-radius:4px;cursor:pointer;border:1px solid var(--bg-hover)}
.ss-row img:hover{border-color:var(--accent)}
.col{margin:8px 0}
.col-h{cursor:pointer;color:var(--text-dim);font-size:11px;user-select:none;padding:4px 0}
.col-h:hover{color:var(--accent)}
.col-c{display:none;margin-top:8px}
.col-c.open{display:block}
.cb{background:var(--bg);padding:12px;border-radius:4px;font-size:11px;overflow-x:auto;white-space:pre-wrap;word-break:break-all;max-height:400px;overflow-y:auto}
.sd{background:var(--bg);padding:12px;border-radius:4px;font-size:11px;white-space:pre-wrap;max-height:300px;overflow-y:auto}
.flags{margin:8px 0;padding:8px;background:rgba(137,180,250,.1);border-radius:4px;font-size:11px}
.fr{font-size:11px;color:var(--text-dim);margin-top:8px;padding:8px;background:var(--bg);border-radius:4px}
.lb{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.9);z-index:1000;justify-content:center;align-items:center;cursor:pointer}
.lb.open{display:flex}
.lb img{max-width:90%;max-height:90%}
.nd{color:var(--text-muted);font-style:italic}
</style>"""

js = """<script>
function openLb(src){document.getElementById('lbi').src=src;document.getElementById('lb').classList.add('open')}
function closeLb(){document.getElementById('lb').classList.remove('open')}
function togCol(h){h.nextElementSibling.classList.toggle('open');h.textContent=h.textContent.startsWith('\\u25b8')?'\\u25be'+h.textContent.slice(1):'\\u25b8'+h.textContent.slice(1)}
</script>"""

def build_side(run_name, cls, data, shots, scenario):
    h = f'<div class="side {cls}"><h3>{escape(run_name)}</h3>\n'
    h += '<div class="metrics-grid">\n'
    for lbl, key, fmt in [
        ("Rounds", "rounds_used", None),
        ("Tokens In", "total_tokens_in", fmt_tokens),
        ("Tokens Out", "total_tokens_out", fmt_tokens),
        ("Tool Calls", "tool_calls", None),
        ("Tool Errors", "tool_errors", None),
        ("Edits", "edit_count", None),
        ("Time", "total_time_ms", fmt_time),
    ]:
        val = data.get(key)
        if fmt and val is not None: val = fmt(val)
        h += f'<div class="mp"><span class="l">{lbl}</span><span class="v">{val if val is not None else "—"}</span></div>\n'
    h += '</div>\n'
    if data.get("error"):
        h += f'<div style="background:rgba(243,139,168,.1);border:1px solid var(--red);padding:6px;border-radius:4px;margin:6px 0;font-size:11px;word-break:break-word">⚠️ {escape(str(data["error"])[:300])}</div>\n'
    # Screenshots
    sc_shots = {k:v for k,v in shots.items() if scenario in k}
    if sc_shots:
        h += '<div class="screenshots"><label>Screenshots (click to enlarge):</label><div class="ss-row">\n'
        for fname in sorted(sc_shots.keys()):
            h += f'<img src="{sc_shots[fname]}" onclick="openLb(this.src)" title="{escape(fname)}">\n'
        h += '</div></div>\n'
    else:
        h += '<div class="screenshots"><span class="nd">No screenshots</span></div>\n'
    # Fixer report (collapsible)
    fixer = data.get("fixer_report")
    if fixer:
        h += f'<div class="col"><div class="col-h" onclick="togCol(this)">▸ StructuralFixer Report</div><div class="col-c">'
        h += f'<div style="background:var(--bg);padding:10px;border-radius:4px;font-size:11px;white-space:pre-wrap;word-break:break-word;color:var(--green)">{escape(fixer[:1000])}</div>'
        h += '</div></div>\n'
    # Structure dump
    dump = data.get("structure_dump") or ""
    if dump:
        h += '<div class="col"><div class="col-h" onclick="togCol(this)">▸ Structure Dump</div><div class="col-c">'
        if "--- structural_flags ---" in dump:
            main, flags = dump.split("--- structural_flags ---")
            h += f'<div class="sd">{escape(main.strip())}</div>'
            h += f'<div class="flags">{escape(flags.strip())}</div>'
        else:
            h += f'<div class="sd">{escape(dump)}</div>'
        h += '</div></div>\n'
    else:
        h += '<div class="col"><div class="col-h" onclick="togCol(this)">▸ Structure Dump</div><div class="col-c"><span class="nd">No data</span></div></div>\n'
    # Tool sequence
    seq = data.get("tool_call_sequence",[])
    if seq:
        h += f'<div class="col"><div class="col-h" onclick="togCol(this)">▸ Tool Sequence ({len(seq)} calls)</div><div class="col-c"><div class="cb">{escape(", ".join(seq))}</div></div></div>\n'
    # Final response
    resp = data.get("final_response_text","") or ""
    if resp:
        h += f'<div class="col"><div class="col-h" onclick="togCol(this)">▸ Final Response</div><div class="col-c"><div class="fr">{escape(resp[:2000])}</div></div></div>\n'
    h += '</div>\n'
    return h

# Build HTML
html = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>BloxBench Comparison</title>'
html += css + '</head><body>\n'
html += '<h1>BloxBench — Side by Side</h1>\n'
html += f'<p class="subtitle">No gates. No judge. You decide. {len(all_scenarios)} evals, two runs.</p>\n'

# Run names shown clearly
html += '<div class="run-selector">\n'
html += f'<span style="color:var(--mauve);padding:6px 12px;background:var(--bg-card);border-radius:6px;font-weight:bold">{escape(LEFT_RUN)}</span>\n'
html += f'<span style="color:var(--text-dim);padding:6px 0">vs</span>\n'
html += f'<span style="color:var(--blue);padding:6px 12px;background:var(--bg-card);border-radius:6px;font-weight:bold">{escape(RIGHT_RUN)}</span>\n'
html += '</div>\n'

# Summary cards (metrics only, no pass/fail)
html += '<div class="summary">\n'
for cls, run_name, summ in [("left", LEFT_RUN, left["data"].get("summary", {})), ("right", RIGHT_RUN, right["data"].get("summary", {}))]:
    run_data = ALL_RUNS.get(run_name, {}).get("data", {})
    html += f'<div class="summary-card {cls}"><h3>{escape(run_name)}</h3>'
    html += f'<div class="metric"><span class="metric-label">Model</span><span class="metric-value">{escape(str(run_data.get("model",{}).get("name","?")))}</span></div>'
    html += f'<div class="metric"><span class="metric-label">Mode</span><span class="metric-value">{escape(str(run_data.get("mode","?")))}</span></div>'
    html += f'<div class="metric"><span class="metric-label">Avg Rounds</span><span class="metric-value">{summ.get("avg_llm_calls","?")}</span></div>'
    html += f'<div class="metric"><span class="metric-label">Avg Tokens In</span><span class="metric-value">{fmt_tokens(summ.get("avg_tokens_in"))}</span></div>'
    html += f'<div class="metric"><span class="metric-label">Avg Tokens Out</span><span class="metric-value">{fmt_tokens(summ.get("avg_tokens_out"))}</span></div>'
    html += f'<div class="metric"><span class="metric-label">Tool Error Rate</span><span class="metric-value">{summ.get("tool_error_rate","?")}%</span></div>'
    html += f'<div class="metric"><span class="metric-label">Avg Edits</span><span class="metric-value">{summ.get("avg_edit_count","?")}</span></div>'
    html += '</div>\n'
html += '</div>\n'

# Nav
html += '<div class="nav">\n'
for sc in all_scenarios:
    short = sc.replace("VB_BUILD_","").replace("VB_UI_","UI:").replace("VB_GAMEPLAY_","GP:")
    html += f'<a class="nav-item" href="#{sc}">{short}</a>\n'
html += '</div>\n'

# Eval sections
for sc in all_scenarios:
    l = left_evals.get(sc,{})
    r = right_evals.get(sc,{})
    short = sc.replace("VB_BUILD_","").replace("VB_UI_","UI:").replace("VB_GAMEPLAY_","GP:")
    prompt = EVAL_PROMPTS.get(sc, "")
    html += f'<div class="eval-section" id="{sc}">\n'
    html += f'<div class="eval-header"><span class="eval-name">{short}</span></div>\n'
    if prompt:
        html += f'<div class="eval-prompt">{escape(prompt)}</div>\n'
    html += '<div class="comparison">\n'
    html += build_side(LEFT_RUN, "left", l, left["shots"], sc)
    html += build_side(RIGHT_RUN, "right", r, right["shots"], sc)
    html += '</div>\n</div>\n'

html += '<div class="lb" id="lb" onclick="closeLb()"><img id="lbi"></div>\n'
html += js + '</body></html>'

out = Path(__file__).parent / "results.html"
out.write_text(html)
print(f"Written {out} ({len(html)/1024:.0f}KB)")
print(f"Left: {LEFT_RUN}")
print(f"Right: {RIGHT_RUN}")
