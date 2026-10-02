<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 1. Kø-utvelgelse (med ekte deps-gating)

→ Kjerne: `coordinator-runbook.md` § 1 · Begrunnelser: `runbook-hvorfor.md` § 1

**Først releasen:**

```bash
python3 tasks/release.py status
```

Exit 2 (`FEIL`: flere aktive releaser, eller en todo som peker på en release som ikke finnes) er et
pausepunkt. Rett fila først; ellers velger skriptet under feil scope. Exit 0 og 1 går videre.

Kjør så dette python-skriptet — det resolver `deps`, ekskluderer claimed/brainstorm, og sorterer prioritert-først:

```bash
python3 - <<'PY'
import glob, os, re
def fm(p):
    t = open(p).read()
    m = re.search(r'^---\n(.*?)\n---', t, re.S)
    d = {}
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r'(\w+):\s*(.*)', line)
            if mm:   # innholdet i "…", ellers alt før en ` #`-kommentar (samme regel som release.py)
                v = mm.group(2).strip(); q = re.match(r'"([^"]*)"', v)
                d[mm.group(1)] = q.group(1) if q else re.sub(r'\s+#.*$', '', v)
    body = t[m.end():] if m else t    # kun kroppen — IKKE frontmatteren (TODO 174: et fritekstfelt
                                       # som `observed:`/`saves:` med ordet «brainstorm» i prosa
                                       # skal ikke stille sende en todo ut av køen)
    d['_brainstorm'] = bool(re.search(r'krever[^.\n]*brainstorm|brainstorm\s+f.?r\s+plan|spec\s+f.?r\s+plan', body, re.I))
    d['_path'] = p
    return d
def as_int(v, default=9999):
    try: return int(v)
    except (ValueError, TypeError): return default
# Aktiv release: bare todoer med `release: <versjon>` er kvalifisert. Uten aktiv release gjelder
# hele køen, som før. Prod-release-todoen eies av mennesket og er aldri kvalifisert.
active = [p for p in glob.glob('tasks/releases/*.md')
          if not p.endswith('/README.md') and fm(p).get('status') == 'active']
rel = os.path.basename(active[0])[:-3] if len(active) == 1 else None
outside = 0
todos = {}
for p in glob.glob('tasks/todos/todo-*.md'):
    d = fm(p); nr = d.get('nr','')
    if not nr:
        print(f"ADVARSEL: mangler nr i {p}"); continue
    todos[nr] = d                                    # parse hver fil ÉN gang
def dep_done(nr):
    f = todos.get(nr)
    return f is None or f.get('status') == 'done'    # mangler fil ⟹ arkivert
rows = []
for nr, d in todos.items():
    deps = re.findall(r'"([^"]+)"', d.get('deps','') or '')
    tags_raw = d.get('tags', '')
    eligible = (d.get('status') in ('open','reviewed') and (d.get('claimed_by','null') in ('null','',None))
                and not d['_brainstorm'] and all(dep_done(x) for x in deps)
                and not re.search(r'\bforslag\b|\bprod-release\b', tags_raw))
    if eligible and rel and d.get('release') != rel:
        eligible, outside = False, outside + 1
    pr = 0 if d.get('priority')=='prioritert' else 1
    rows.append((pr, as_int(d.get('order')), nr, d.get('status','?'), 'YES' if eligible else 'no', d['_path']))
for r in sorted(rows):
    print(f"elig={r[4]:3} pri={r[0]} order={r[1]:5} TODO {r[2]:5} {r[3]:10} {r[5]}")
open_todos = [d for d in todos.values() if d.get('status') == 'open']
loop_todos = [d for d in open_todos if re.search(r'\bloop\b', d.get('tags', '') or '')]
print(f"\nKø-sammensetning: {len(loop_todos)} av {len(open_todos)} åpne todos er loop-taggede.")
if rel:
    print(f"Release {rel}: {outside} ellers kvalifiserte todoer står utenfor scope og venter.")
PY
```

Velg øverste rad med `elig=YES`. **Ingen kvalifisert** → se på DOM-linja fra `release.py status`:

- `MÅL NÅDD` eller `MÅL IKKE NÅDD` (exit 1) → pausepunkt «release». Meld DOM-linja og fremdriften
  ordrett til mennesket og stopp. Ved `MÅL NÅDD` er neste steg prod-release-todoen, og den tar
  mennesket.
- `PÅGÅR` → det finnes åpne todoer i scope, men ingen er kvalifisert (deps, brainstorm, claimet).
  Pausepunkt «release»: list dem med grunn. Ikke hent arbeid utenfor scope uten menneskets ord.
- `INGEN AKTIV RELEASE` → §7 (grooming), som før. **Kø-sammensetning-linjen er ren
rapportering** (TODO 174, Del C′) — den påvirker ALDRI valget over. Se «Du styrer køen
(rattet)» i `orchestration-loop.md` for hvordan mennesket bruker den (`priority: prioritert`
på en `loop`-tagget todo hvis loop-forbedringer sulter).

**TODO 246 — nivå B3:** dette valget (og et bevisst HOPP forbi øverste `elig=YES`-rad, innenfor
mennesket-godkjent rekkefølge) er nivå B3 i `decision-level.py`. Logg kun ved et FAKTISK hopp/valg
utenom triviell «øverste rad vant» — se § Pausepunkter for de fire logg-pliktene.
