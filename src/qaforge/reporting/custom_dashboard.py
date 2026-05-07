"""
qaforge.reporting.custom_dashboard
==================================
Renders a single-file static HTML dashboard from the Extent JSON report.
No server, no JS dependencies — fully shareable as `reports/custom/dashboard.html`.
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from qaforge.reporting.extent_reporter import ExtentReporter

OUT_DIR = Path(__file__).resolve().parents[3] / "reports" / "custom"
OUT_DIR.mkdir(parents=True, exist_ok=True)

_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>QAForge Run — {{ run.environment }}</title>
<style>
  :root {--g:#16a34a;--r:#dc2626;--y:#ca8a04;--bg:#0b1020;--fg:#e6edf3;--card:#111835;--mut:#94a3b8}
  *{box-sizing:border-box}
  body{background:var(--bg);color:var(--fg);font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;margin:0;padding:24px}
  h1{margin:0 0 4px}
  .sub{color:var(--mut);margin-bottom:24px}
  .grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
  .card{background:var(--card);border-radius:12px;padding:16px}
  .num{font-size:28px;font-weight:700}
  .pass{color:var(--g)} .fail{color:var(--r)} .skip{color:var(--y)}
  table{width:100%;border-collapse:collapse;background:var(--card);border-radius:12px;overflow:hidden}
  th,td{padding:10px 14px;text-align:left;border-bottom:1px solid #1f2937;font-size:14px}
  th{background:#0f172a;color:var(--mut);font-weight:600}
  .pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}
  .pill.passed{background:#052e1c;color:var(--g)}
  .pill.failed{background:#3a0d10;color:var(--r)}
  .pill.skipped{background:#3b2807;color:var(--y)}
  .tag{display:inline-block;background:#1e293b;color:#cbd5e1;padding:2px 6px;border-radius:6px;font-size:11px;margin-right:4px}
  details summary{cursor:pointer;color:#7dd3fc}
  pre{white-space:pre-wrap;background:#020617;padding:8px;border-radius:6px;font-size:12px}
</style></head><body>
<h1>QAForge — Test Run Dashboard</h1>
<div class="sub">Environment: <b>{{ run.environment }}</b> · Total: {{ run.total }} · Passed: {{ run.passed }} · Failed: {{ run.failed }} · Skipped: {{ run.skipped }}</div>
<div class="grid">
  <div class="card"><div class="sub">Total</div><div class="num">{{ run.total }}</div></div>
  <div class="card"><div class="sub">Passed</div><div class="num pass">{{ run.passed }}</div></div>
  <div class="card"><div class="sub">Failed</div><div class="num fail">{{ run.failed }}</div></div>
  <div class="card"><div class="sub">Skipped</div><div class="num skip">{{ run.skipped }}</div></div>
</div>
<table>
  <thead><tr><th>Feature</th><th>Scenario</th><th>Status</th><th>Duration (ms)</th><th>Tags</th><th>Details</th></tr></thead>
  <tbody>
  {% for s in run.scenarios %}
    <tr>
      <td>{{ s.feature }}</td>
      <td>{{ s.name }}</td>
      <td><span class="pill {{ s.status }}">{{ s.status }}</span></td>
      <td>{{ '%.0f' % s.duration_ms }}</td>
      <td>{% for t in s.tags %}<span class="tag">{{ t }}</span>{% endfor %}</td>
      <td><details><summary>steps ({{ s.steps|length }})</summary>
        <table>{% for st in s.steps %}<tr>
          <td><span class="pill {{ st.status }}">{{ st.status }}</span></td>
          <td><b>{{ st.keyword }}</b> {{ st.name }}</td>
          <td>{{ '%.0f' % st.duration_ms }} ms</td>
        </tr>{% if st.error %}<tr><td colspan="3"><pre>{{ st.error }}</pre></td></tr>{% endif %}{% endfor %}</table>
      </details></td>
    </tr>
  {% endfor %}
  </tbody>
</table>
</body></html>
"""


def render_dashboard() -> Path:
    rep = ExtentReporter()
    html = Template(_TEMPLATE).render(run=rep.run)
    out = OUT_DIR / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    return out
