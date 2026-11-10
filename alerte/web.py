"""Local test interface for ALERTE (standard library only, no extra install).

Usage:  python -m alerte.web   then open http://localhost:8000
Tabs: legal search, scenarios (with answer key), mandate table, deterministic checks.
"""
from __future__ import annotations

import contextlib
import csv
import io
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
KNOW, SCN = ROOT / "knowledge", ROOT / "scenarios"


def rows(name: str) -> list[dict]:
    return list(csv.DictReader(open(KNOW / name, encoding="utf-8")))


def run_main(fn) -> dict:
    """Run a command-line check and capture what it prints."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn()
    return {"ok": code == 0, "output": buf.getvalue()}


def api(path: str, q: dict) -> object:
    g = lambda k, d=None: q.get(k, [d])[0]
    if path == "/api/search":
        from alerte.kb.index import search
        titles = {r["id"]: r["title"] for r in rows("manifest.csv")}
        res = search(g("q", ""), k=int(g("k", 5)), country=g("country") or None)
        return [{"chunk_id": r["chunk_id"], "title": titles.get(r["doc_id"], ""), "country": r["country"],
                 "score": r["score"], "text": r["text"][:1500]} for r in res]
    if path == "/api/scenarios":
        out = {}
        for p in sorted(SCN.glob("[A-Z][A-Z]-*.yaml")):
            out[p.stem] = yaml.safe_load(p.read_text(encoding="utf-8"))
        return {"scenarios": out, "gaps": yaml.safe_load((SCN / "gaps.yaml").read_text(encoding="utf-8"))}
    if path == "/api/mandates":
        return {"mandates": rows("mandates.csv"), "precedents": rows("precedents.csv")}
    if path == "/api/check/scenarios":
        from alerte.scenario.validate import main
        return run_main(main)
    if path == "/api/check/quotes":
        from alerte.kb.check_quotes import main
        return run_main(main)
    if path == "/api/stats":
        man = rows("manifest.csv")
        n = sum(1 for _ in open(KNOW / "chunks.jsonl", encoding="utf-8"))
        by = {}
        for r in man:
            by.setdefault(r["country"], 0)
            by[r["country"]] += 1
        return {"sources": len(man), "chunks": n, "mandates": len(rows("mandates.csv")),
                "precedents": len(rows("precedents.csv")), "by_country": by}
    return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            body, ctype = PAGE.encode(), "text/html; charset=utf-8"
        else:
            try:
                data = api(u.path, parse_qs(u.query))
            except Exception as e:  # show the error in the page rather than crash
                data = {"error": str(e)}
            if data is None:
                self.send_error(404)
                return
            body, ctype = json.dumps(data, ensure_ascii=False).encode(), "application/json"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ALERTE - Tests</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1c2430;--mute:#5b6675;--line:#dde2e8;--acc:#0b5cad;
--gap:#b42318;--partial:#b54708;--covered:#067647;--na:#475467}
@media (prefers-color-scheme:dark){:root{--bg:#12161c;--card:#1b2129;--ink:#e6e9ee;--mute:#9aa4b2;
--line:#2c3540;--acc:#5aa2f0;--gap:#f97066;--partial:#fdb022;--covered:#47cd89;--na:#98a2b3}}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--ink)}
header{padding:14px 16px;border-bottom:1px solid var(--line);background:var(--card)}
header h1{margin:0;font-size:18px}.banner{font-size:13px;color:var(--mute)}
nav{display:flex;gap:4px;flex-wrap:wrap;padding:8px 16px;background:var(--card);border-bottom:1px solid var(--line)}
nav button{border:1px solid var(--line);background:none;color:var(--ink);padding:6px 12px;border-radius:6px;cursor:pointer}
nav button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
main{max-width:1100px;margin:0 auto;padding:16px}section{display:none}section.on{display:block}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;margin:10px 0}
input,select{font:inherit;padding:7px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
input[type=text]{flex:1;min-width:200px}.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.go{background:var(--acc);color:#fff;border:0;padding:8px 14px;border-radius:6px;cursor:pointer;font:inherit}
.id{font-family:ui-monospace,monospace;font-size:13px;color:var(--acc)}.mute{color:var(--mute);font-size:13px}
pre{white-space:pre-wrap;font-size:13px;margin:6px 0 0;max-height:240px;overflow:auto}
.tag{display:inline-block;font-size:12px;padding:1px 7px;border-radius:10px;border:1px solid currentColor;margin-right:4px}
.gap{color:var(--gap)}.partial{color:var(--partial)}.covered{color:var(--covered)}.not_assessable{color:var(--na)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.stat b{display:block;font-size:24px}table{width:100%;border-collapse:collapse;font-size:13px}
td,th{border-bottom:1px solid var(--line);padding:6px;text-align:left;vertical-align:top}
.wrap{overflow-x:auto}.ok{color:var(--covered);font-weight:600}.ko{color:var(--gap);font-weight:600}
</style></head><body>
<header><h1>ALERTE - interface de test</h1><div class="banner">EXERCICE FICTIF - aucun de ces événements n'a eu lieu.</div></header>
<nav><button data-t="home" class="on">Accueil</button><button data-t="search">Recherche dans la loi</button>
<button data-t="scn">Scénarios</button><button data-t="mand">Mandats</button><button data-t="check">Contrôles</button></nav>
<main>
<section id="home" class="on"><div class="stats" id="stats"></div>
<div class="card">Cette page teste ce qui est construit : la base de connaissances (recherche), les scénarios et leurs réponses attendues, le tableau des mandats et les contrôles automatiques (sans IA). Les agents ne sont pas encore branchés.</div></section>
<section id="search"><div class="card"><div class="row">
<input type="text" id="q" placeholder="ex. who can order operators to send an alert ?">
<select id="cc"><option value="AE">Émirats</option><option value="CM">Cameroun</option><option value="GL">International</option><option value="">Tous</option></select>
<select id="k"><option>3</option><option selected>5</option><option>10</option></select>
<button class="go" id="sgo">Chercher</button></div>
<div class="mute" style="margin-top:6px">Exemples :
<a href="#" class="ex">who can order operators to send an alert</a> ·
<a href="#" class="ex" data-c="CM">qui peut ordonner aux opérateurs de diffuser une alerte</a> ·
<a href="#" class="ex">false news during an emergency</a> ·
<a href="#" class="ex">transfer of personal data abroad</a></div></div><div id="sres"></div></section>
<section id="scn"><div class="card row"><select id="sid"></select><label><input type="checkbox" id="key" checked> Afficher la réponse attendue</label></div><div id="sbody"></div></section>
<section id="mand"><div class="card row"><select id="mc"><option value="AE">Émirats</option><option value="CM">Cameroun</option></select>
<input type="text" id="mf" placeholder="filtrer (institution, action, texte)"></div><div class="card wrap"><table id="mt"></table></div></section>
<section id="check"><div class="card row"><button class="go" data-c="scenarios">Vérifier les scénarios</button>
<button class="go" data-c="quotes">Vérifier les citations</button></div><div id="cout"></div></section>
</main>
<script>
const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const J=u=>fetch(u).then(r=>r.json());
const OUT={gap:'lacune',partial:'partiel',covered:'couvert',not_assessable:'non évaluable'};
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{document.querySelectorAll('nav button,section').forEach(x=>x.classList.remove('on'));b.classList.add('on');$('#'+b.dataset.t).classList.add('on')});
J('/api/stats').then(s=>{$('#stats').innerHTML=[['Sources',s.sources],['Articles découpés',s.chunks],['Lignes de mandat',s.mandates],['Précédents étrangers',s.precedents]].map(([a,b])=>`<div class="card stat"><b>${b}</b>${a}</div>`).join('')+`<div class="card stat mute">Par pays : ${Object.entries(s.by_country).map(([k,v])=>k+' '+v).join(', ')}</div>`});
async function doSearch(){const q=$('#q').value.trim();if(!q)return;$('#sres').innerHTML='<div class="card mute">Recherche... (le premier appel charge le modèle, environ 20 s)</div>';
const r=await J(`/api/search?q=${encodeURIComponent(q)}&country=${$('#cc').value}&k=${$('#k').value}`);
if(r.error){$('#sres').innerHTML=`<div class="card ko">${esc(r.error)}</div>`;return}
$('#sres').innerHTML=r.length?r.map((x,i)=>`<div class="card"><b>${i+1}.</b> <span class="id">${esc(x.chunk_id)}</span> <span class="mute">${esc(x.title)} · score ${x.score}</span><pre>${esc(x.text)}</pre></div>`).join(''):'<div class="card">Aucun résultat.</div>'}
$('#sgo').onclick=doSearch;$('#q').onkeydown=e=>{if(e.key==='Enter')doSearch()};
document.querySelectorAll('.ex').forEach(a=>a.onclick=e=>{e.preventDefault();$('#q').value=a.textContent;$('#cc').value=a.dataset.c||'AE';doSearch()});
let S;J('/api/scenarios').then(d=>{S=d;$('#sid').innerHTML=Object.entries(d.scenarios).map(([k,v])=>`<option value="${k}">${k} - ${esc(v.title)}</option>`).join('');showScn()});
$('#sid').onchange=showScn;$('#key').onchange=showScn;
function showScn(){const s=S.scenarios[$('#sid').value],key=$('#key').checked;let act=0,h=`<div class="card"><b>${esc(s.title)}</b><div class="mute">${esc(s.banner)} · relu par : ${esc(s.reviewed_by)}</div></div>`;
for(const e of s.events){if(e.act!==act){act=e.act;h+=`<h3>Acte ${act} - ${esc(s.acts[act])}</h3>`}
h+=`<div class="card"><span class="id">${e.id}</span> <b>${esc(e.t)}</b> <span class="mute">source : ${esc(e.source)} → ${e.to.map(esc).join(', ')}${e.optional?' · optionnel':''}${e.contradicts?' · contredit '+e.contradicts:''}</span><div>${esc(e.content)}</div>`;
if(e.hydrosense){const v=e.hydrosense;h+=`<div class="mute">HydroSense : ${v.sensors_active}/7 capteurs, données de ${v.data_age_min} min → ${v.validity_met?'<span class="ok">condition de validité respectée</span>':'<span class="ko">hors condition de validité</span>'}</div>`}
if(key){h+=`<div style="margin-top:6px">${e.expected.map(x=>`<span class="tag ${x.outcome}">${x.gap} : ${OUT[x.outcome]}${x.confidence?' (confiance '+x.confidence+')':''}</span>`).join('')} <span class="mute">action testée : ${esc(e.tests_action)}</span></div>
<div class="mute">${e.expected.map(x=>`${x.gap} - ${esc(S.gaps[x.gap].title)} · textes : ${x.law_refs.join(', ')} · précédents : ${x.precedents.join(', ')||'aucun'}${x.note?' · '+esc(x.note):''}`).join('<br>')}</div>
<div class="mute"><b>Bon comportement :</b> ${esc(e.good_behaviour)}</div>`}h+='</div>'}$('#sbody').innerHTML=h}
let M;J('/api/mandates').then(d=>{M=d.mandates;showM()});$('#mc').onchange=showM;$('#mf').oninput=showM;
function showM(){const f=$('#mf').value.toLowerCase(),r=M.filter(x=>x.country===$('#mc').value&&(!f||JSON.stringify(x).toLowerCase().includes(f)));
$('#mt').innerHTML='<tr><th>ID</th><th>Institution</th><th>Action</th><th>Type</th><th>Article</th><th>Citation</th><th>Preuve</th></tr>'+r.map(x=>`<tr><td class="id">${x.id}</td><td>${esc(x.institution)}</td><td>${esc(x.action)}</td><td>${esc(x.kind)}</td><td class="id">${esc(x.chunk_id)}</td><td>${esc(x.quote)||'<span class="mute">'+esc(x.note)+'</span>'}</td><td>${esc(x.evidence)}</td></tr>`).join('')}
document.querySelectorAll('[data-c]').forEach(b=>{if(b.tagName==='BUTTON')b.onclick=async()=>{$('#cout').innerHTML='<div class="card mute">Contrôle en cours...</div>';const r=await J('/api/check/'+b.dataset.c);
$('#cout').innerHTML=`<div class="card"><span class="${r.ok?'ok':'ko'}">${r.ok?'RÉUSSI':'ÉCHEC'}</span>${r.error?' '+esc(r.error):''}<pre style="max-height:none">${esc(r.output)}</pre></div>`}});
</script></body></html>"""


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"ALERTE test interface: http://localhost:{port}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
