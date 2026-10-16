"""Theodor 16.10.2026: skjermbilder av stjerneraden (2 hele + 2 tapte + 1 tom) i 16/24/32 px, lys og mørk, med appens egen CSS og starsSVG.

  python3 tools/stjerner_skjermbilder.py [for|etter]   → docs/design/stjerner/<tag>_lys.png og _mork.png"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(ROOT / "fetcher"))
import testserver
tag = sys.argv[1] if len(sys.argv) > 1 else "etter"   # «for»/«etter»
srv, port = testserver.serve(str(ROOT / "docs"))
HTML = """<!doctype html><html><head><meta charset=utf-8><link rel=stylesheet href=css/app.css><link rel=stylesheet href=css/ui.css>
<style>body{margin:0;padding:24px;background:var(--surface);font-family:var(--body);color:var(--ink)} .row{display:flex;gap:28px;align-items:center;margin:14px 0}
.s16 .stars svg{width:16px;height:16px}.s24 .stars svg{width:24px;height:24px}.s32 .stars svg{width:32px;height:32px} .lbl{width:56px;font:12px var(--mono);white-space:nowrap}</style></head>
<body><div id=out></div><script src=js/strings.js></script><script src=js/app.js></script><script>
const o=document.getElementById('out');
for(const px of [16,24,32]){ let h=`<div class="row s${px}"><span class=lbl>${px} px</span>`;
  for(const r of [1,2,3,4]) h+=`<span class="r-${r}">${starsSVG(Math.min(r,2),2,false)}</span>`; o.innerHTML+=h+'</div>'; }
</script></body></html>"""
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        for scheme in ("light", "dark"):
            pg = b.new_page(viewport={"width": 980, "height": 220}, device_scale_factor=2, color_scheme=scheme)
            pg.set_default_timeout(15000)
            pg.route("**/stjerner.html", lambda r, req: r.fulfill(status=200, content_type="text/html", body=HTML))
            pg.goto(f"http://127.0.0.1:{port}/stjerner.html"); pg.wait_for_timeout(500)
            pg.screenshot(path=f"{ROOT}/docs/design/stjerner/{tag}_{'lys' if scheme=='light' else 'mork'}.png", full_page=True)
            pg.close()
        b.close()
finally:
    srv.shutdown()
print("ok", tag)
