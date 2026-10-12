"""HTML-målesiden for loopen (kalles av tasks/measure-cost.py --html <sti>).

Kilder: todo-radene fra measure-cost.py (`credits=` i run-loggen / `--credits` fra `/usage`),
`assistant.usage`-hendelsene fra øktenes events.jsonl (når de finnes) og docs/loop/run-log.md
(Gate F-returer, review-runder, utfall). Enheten er AI credits. Et tall uten kilde vises som
`IKKE MÅLT`, aldri som 0. Siden er avledet — rediger aldri HTML-en for hånd; den committes ikke
(kun scratchpad), og publiseres på fast lenke.
"""
import html, os, re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

OSLO = ZoneInfo('Europe/Oslo')
NOT_MEASURED = 'IKKE MÅLT'
ROLES = [  # (nøkkel, visningsnavn, CSS-variabel)
    ('koordinator', 'Koordinator', '--c-koord'),
    ('planner', 'Planner', '--c-plan'),
    ('planreview', 'Plan-review', '--c-preview'),
    ('implementer', 'Implementer', '--c-impl'),
    ('kodereview', 'Kode-review + linser', '--c-review'),
    ('scout', 'Scout', '--c-scout'),
    ('annet', 'Annet', '--c-annet'),
    ('todo', 'Todo (run-log, ikke fordelt på rolle)', '--c-annet'),
]
ROLE_OF = {
    '{{PROJECT_NAME}}-planner': 'planner', '{{PROJECT_NAME}}-reviewer': 'planreview',
    '{{PROJECT_NAME}}-implementer': 'implementer', '{{PROJECT_NAME}}-code-reviewer': 'kodereview',
    'rls-migration-reviewer': 'kodereview', 'race-reviewer': 'kodereview',
    'ios-design-reviewer': 'kodereview', 'edge-function-reviewer': 'kodereview',
    '{{PROJECT_NAME}}-scout': 'scout',
}


def role(t):
    """Agentnavnet i en `assistant.usage`-hendelse → rolle. Uten agentnavn er kallet koordinatorens."""
    if not t:
        return 'koordinator'
    if t == 'todo':
        return 'todo'
    return ROLE_OF.get(t, 'annet')


def local(ts):
    d = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    if d.tzinfo is None:  # tidsstempler uten sone (f.eks. --cutover) er UTC, som øktloggene
        d = d.replace(tzinfo=ZoneInfo('UTC'))
    return d.astimezone(OSLO)


def model_short(m):
    """Modellnavnet slik det står i hendelsen, kortet ned for tabellen."""
    m = m or '?'
    return m if len(m) <= 28 else m[:27] + '…'


def coordinator_calls(events):
    """Én rad per koordinatorkall (hendelse uten agentnavn): (ts, credits|None, kontekst, modell, effort, output)."""
    return [(u['ts'], u['credits'], u['ctx'], u['model'], u.get('effort') or '?', u['out'])
            for u in events if not u.get('agent') and u.get('ts')]


def cr_sum(vals):
    """Summen av målte credits, None når ingen verdi er målt (aldri 0 for «ingen data»)."""
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def run_log(path):
    """nr → siste rad: utfall, review-runder, gate F-returer."""
    res = {}
    if not os.path.exists(path):
        return res
    for line in open(path, encoding='utf-8'):
        c = [x.strip() for x in line.split(' | ')]
        if len(c) < 11 or not re.match(r'\d{4}-\d\d-\d\dT', c[0]) or c[1] in ('-', ''):
            continue
        m = re.search(r'gate_f_returns=(?:r\d+:)?(\d+)', c[10])
        pr = re.search(r'/pull/(\d+)', c[5])
        res[c[1]] = {'ts': c[0], 'outcome': c[3], 'plan_rounds': c[6], 'review_rounds': c[7],
                     'gate_f': int(m.group(1)) if m else None, 'pr': pr.group(1) if pr else None}
    return res


def esc(s):
    return html.escape(str(s))


def money(x):
    """AI credits for visning. None → IKKE MÅLT."""
    if x is None:
        return NOT_MEASURED
    return f'{x:,.0f} cr' if x >= 100 else f'{x:,.2f} cr'


# Tiltak uten egen decision-log-rad: (tidspunkt, tittel, tekst, kilde). Tom som standard.
EXTRA_MILESTONES = []

# Rader i decision-log som er TILTAK på loopen selv, ikke beslutninger om én todo.
MEASURE_ROW = re.compile(
    r'^### (\d{4}-\d\d-\d\d) (\d\d:\d\d) — (§8c \[B\]|\[kostnadsgrep\]|\[modellbytte\]|\[tiltak\]|§6c[^:]*\[B\]):\s*(.+)$')


def _loop_doc(here, name):
    return os.path.join(here, '..', 'docs', 'loop', name)


def milestones(here):
    """Tiltakene, lest fra decision-log — ÉN kilde for både grafmarkørene og tiltakslista.

    Hardkodet liste var forrige form. Den ville drevet fra loggen i det et tiltak ble
    innført uten at noen husket å oppdatere grafen, og markøren ville da pekt på et
    tidspunkt uten hendelse mens den ekte hendelsen var usynlig.
    """
    path = _loop_doc(here, 'decision-log.md')
    out = [(f'{d}', t, desc, src) for d, t, desc, src in EXTRA_MILESTONES]
    if os.path.exists(path):
        lines = open(path, encoding='utf-8').read().splitlines()
        for i, line in enumerate(lines):
            m = MEASURE_ROW.match(line)
            if not m:
                continue
            date, tm, kind, title = m.groups()
            body = ''
            for nxt in lines[i + 1:i + 8]:
                if nxt.startswith('### '):
                    break
                if nxt.strip():
                    body = nxt.strip()
                    break
            out.append((f'{date} {tm}', title.strip(), body, kind))
    out.sort(key=lambda x: x[0])
    return out


def ms_points(ms):
    """(iso_ts, kort etikett) for grafmarkørene."""
    res = []
    for ts, title, _, _ in ms:
        short = title.split('—')[0].split(':')[0].strip()
        if len(short) > 22:
            short = short[:21] + '…'
        res.append((ts.replace(' ', 'T'), short))
    return res


def _epoch(ts):
    return local(ts).timestamp()


# Serie-registeret: navn og gate-flagg ÉN gang, lest av både `trend_section`
# (chip-farge i grafen) og `trend_report` (exit-kode i §8c). Flagget lå først bare i
# rapporten, og grafen rendret rød chip på «kostnad per dag» mens rapporten sa
# «kontekst» — to kilder til samme sannhet, altså nøyaktig divergensen `normalize`
# ble trukket ut for å fjerne.
#
# `gate` = kan målingen utløse §8c-plikt? «kostnad per dag» kan IKKE: målt
# er r = 0,963 mot antall agentkjøringer per dag, så den måler hvor mye vi jobbet, ikke
# hvor effektivt. Som gate ville den fyrt hver gang vi jobbet mye — rød av feil grunn,
# speilvendt av en vakt som aldri kan bli rød. Beholdes som kontekst.
SERIES = {
    'cost': ('kostnad per levert todo', True),
    'rounds': ('kode-review-runder per todo', True),
    'gatef': ('gate F-returer per todo', True),
    'daily': ('kostnad per dag', False),
}


def _num(v):
    """Én definisjon av «er dette et tall» for begge trend-funksjonene.

    `trend_section` brukte `try: float(...) except`, `trend_report` brukte
    `str(...).isdigit()`. De er ikke ekvivalente — `'-1'` og `' 3'` passerer bare den
    første, og `'²'` passerer `isdigit()` men får `float()` til å kaste. Ingen
    divergerende verdi finnes i dagens run-log, men to kilder til samme serie er
    akkurat det `SERIES` ble innført for å fjerne.
    """
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _verdict(vals, lower_is_better=True, window=5):
    """Snitt av siste N mot de N før. Returnerer (pil, klasse, tekst) eller None.

    Krever minst 2 × 3 punkter. Under det er «trenden» støy, og en pil ville påstått
    en retning dataene ikke bærer — samme feilklasse som en vakt som alltid er grønn.
    """
    n = min(window, len(vals) // 2)
    if n < 3:
        return None
    before = sum(vals[-2 * n:-n]) / n
    after = sum(vals[-n:]) / n
    if before == 0:
        # Null-baseline. Returnerte tidligere None, som renderes som «for få punkter
        # til en retning» — usant for en serie med nok punkter, og den teksten kan
        # aldri bli FEIL VEI. Det rammet nettopp serien der 0 ER måltilstanden:
        # Gate F-returer har nådd 0, så en full regresjon ville blitt meldt som
        # «for få punkter» med exit 0.
        if after == 0:
            return ('→', 'flat', f'uendret (0 begge vinduer, siste {n} mot forrige {n})')
        # Pilen følger FORTEGNET (verdien steg), dommen følger `lower_is_better`.
        # Første form snudde pilen sammen med dommen og påsto nedgang på en serie som
        # hadde steget — samme sammenblanding av «retning» og «bra/dårlig» som
        # `SERIES` ble innført for å avslutte.
        return ('↑', 'bad' if lower_is_better else 'good',
                f'fra 0 til {after:.2f} i snitt — baselinen var null, '
                f'siste {n} mot forrige {n}')
    pct = (after - before) / before * 100
    if abs(pct) < 5:
        return ('→', 'flat', f'uendret ({pct:+.0f} %)')
    good = (pct < 0) if lower_is_better else (pct > 0)
    return ('↓' if pct < 0 else '↑', 'good' if good else 'bad',
            f'{pct:+.0f} % siste {n} mot forrige {n}')


def sparkline(points, fmt_y, ms_pts, lower_is_better=True, is_gate=True):
    """points: [(iso_ts, verdi, etikett)] sortert stigende. Inline SVG, ingen library."""
    if len(points) < 2:
        return '<p class="muted">For få datapunkter til en trend.</p>'
    W, H, PAD_T, PAD_B = 600.0, 96.0, 12.0, 20.0
    xs = [_epoch(p[0]) for p in points]
    ys = [p[1] for p in points]
    x0, x1 = min(xs), max(xs)
    span = (x1 - x0) or 1.0
    top = max(ys) * 1.12 or 1.0

    def px(t):
        return (t - x0) / span * W

    def py(v):
        return PAD_T + (1 - v / top) * (H - PAD_T - PAD_B)

    body = []
    # Tiltaksmarkører først, så de ligger bak linja.
    for ts, label in ms_pts:
        t = _epoch(ts)
        if not (x0 <= t <= x1):
            continue
        x = px(t)
        body.append(f'<line x1="{x:.1f}" y1="{PAD_T - 6:.1f}" x2="{x:.1f}" y2="{H - PAD_B:.1f}" '
                    f'class="ms"/>')
        anchor = 'start' if x < W * 0.75 else 'end'
        dx = 4 if anchor == 'start' else -4
        body.append(f'<text x="{x + dx:.1f}" y="{PAD_T - 1:.1f}" text-anchor="{anchor}" '
                    f'class="ms-t">{esc(label)}</text>')

    pts = ' '.join(f'{px(t):.1f},{py(v):.2f}' for t, v in zip(xs, ys))
    area = f'M {px(xs[0]):.1f},{H - PAD_B:.1f} L ' + ' L '.join(
        f'{px(t):.1f},{py(v):.2f}' for t, v in zip(xs, ys)) + f' L {px(xs[-1]):.1f},{H - PAD_B:.1f} Z'
    body.append(f'<path d="{area}" class="sp-area"/>')
    body.append(f'<polyline points="{pts}" class="sp-line"/>')
    for (ts, v, lbl), t in zip(points, xs):
        body.append(f'<circle cx="{px(t):.1f}" cy="{py(v):.2f}" r="2.6" class="sp-dot">'
                    f'<title>{esc(lbl)}: {esc(fmt_y(v))}</title></circle>')

    v = _verdict(ys, lower_is_better)
    chip = ''
    if v:
        arrow, cls, txt = v
        # Kontekst-serier får aldri en dom-farge: en rød chip ville sagt «dette er
        # galt» om et tall som ikke utløser noen plikt, og spriket mot `--trend`.
        if not is_gate:
            chip = f'<span class="chip nil">{arrow} {esc(txt)} · kontekst</span>'
        else:
            chip = f'<span class="chip {cls}">{arrow} {esc(txt)}</span>'
    else:
        chip = '<span class="chip nil">for få punkter til en retning</span>'
    return (f'<div class="sp-wrap"><svg viewBox="0 0 {W:.0f} {H:.0f}" preserveAspectRatio="none" '
            f'class="sp" role="img">{"".join(body)}</svg>'
            f'<div class="sp-foot"><span class="mono muted">{esc(fmt_y(min(ys)))} – '
            f'{esc(fmt_y(max(ys)))}</span>{chip}</div></div>')


def tiltak_section(ms):
    """Hva jeg har endret på loopen, og når — lest fra decision-log.

    Finnes fordi decision-log.md er 8000 linjer og 396 rader: §8c-raden for det første
    tiltaket lå på linje 7986. Et tiltak som bare er loggført der, er i praksis ikke
    rapportert. Grafmarkørene over viser NÅR noe skjedde; denne viser HVA.
    """
    if not ms:
        return ''
    h = ['<section><h2>Tiltak på loopen</h2><p class="lede">Endringer jeg har gjort på selve '
         'arbeidsmåten, nyeste først — ikke på appen. Hentet fra <code>decision-log.md</code>, '
         'som er kilden også for de stiplede markørene i kurvene over. '
         'Nivå B betyr at jeg besluttet selv og loggførte; du kan vetoe i etterkant.</p>'
         '<div class="tl">']
    for ts, title, body, src in reversed(ms):
        badge = ('autonom (§8c)' if src.startswith('§8c') else
                 'ikke loggført' if src == 'transkript' else
                 'helsesjekk' if src.startswith('§6c') else 'eier-godkjent')
        cls = ('auto' if src.startswith('§8c') else
               'ext' if src == 'transkript' else 'owner')
        h.append(f'<div class="tl-row"><div class="tl-when mono">{esc(ts[:16])}</div>'
                 f'<div class="tl-what"><div class="tl-head"><strong>{esc(title)}</strong>'
                 f'<span class="tag {cls}">{esc(badge)}</span></div>'
                 f'<p class="tl-body">{esc(body)}</p></div></div>')
    h.append('</div><p class="lede" style="margin-top:12px">Effekten av hvert tiltak leses i '
             'kurvene over: markøren viser når det ble innført, og kurven etter den viser om det '
             'bet. §8c krever at effekten sjekkes ved neste helsesjekk — en gate som er innført og '
             'aldri fyrer er like ofte et tegn på at gaten ikke kan se klassen som på at klassen '
             'er borte.</p></section>')
    return '\n'.join(h)


def _per_todo(rows):
    per = defaultdict(lambda: {'credits': 0.0, 'last': ''})
    for r in rows:
        if r['todo'] == '-':
            continue
        p = per[r['todo']]
        p['credits'] += r['credits']
        p['last'] = max(p['last'], r.get('t1') or r['t0'])
    return per


def _days(rows, events):
    """Credits per lokal dag og rolle. Hendelsene når de har credits, ellers todo-radene.
    Aldri begge: `credits=` i run-loggen er hentet fra `/usage` for de samme kallene."""
    days = defaultdict(lambda: defaultdict(float))
    ev = [u for u in events if u['credits'] is not None and u.get('ts')]
    if ev:
        for u in ev:
            days[local(u['ts']).strftime('%Y-%m-%d')][role(u.get('agent'))] += u['credits']
        return days, 'assistant.usage'
    for r in rows:
        days[local(r['t0']).strftime('%Y-%m-%d')]['todo'] += r['credits']
    return days, 'run-log'


def trend_section(per, rl, days, day_keys, since, ms_pts):
    """Fire tidsserier. Alle fire er «lavere er bedre».

    ALLE seriene filtreres på `since`. Uten det filteret arvet runde- og Gate F-seriene
    hele run-loggens historikk (105 punkter) mens kostnadsserien var begrenset til
    perioden med kostnadsdata (27) — to kurver ved siden av hverandre som dekker ulike
    tidsrom, uten at noe i bildet sier fra.
    """
    merged = sorted(
        ((info['ts'], nr, info) for nr, info in rl.items()
         if info.get('outcome') == 'merged' and info.get('ts') and info['ts'] >= since),
        key=lambda x: x[0])

    cost = [(ts, per[nr]['credits'], f'TODO {nr}') for ts, nr, _ in merged
            if nr in per and per[nr]['credits'] > 0]
    rounds = []
    gatef = []
    for ts, nr, info in merged:
        rv = _num(info.get('review_rounds'))
        if rv is not None:
            rounds.append((ts, rv, f'TODO {nr}'))
        if info.get('gate_f') is not None:
            gatef.append((ts, float(info['gate_f']), f'TODO {nr}'))
    daily = [(f'{d}T12:00', sum(days[d].values()), d[5:]) for d in day_keys]

    cards = [
        ('cost', 'Kostnad per levert todo', 'AI credits per merget todo (`credits=` i run-loggen), i '
         'mergerekkefølge. En todo uten `credits=` er IKKE MÅLT og står ikke i kurven.', cost,
         lambda v: f'{v:,.1f} cr'),
        ('rounds', 'Kode-review-runder per levert todo', 'Hvor mange runder koden måtte gjennom før merge. '
         'Færre runder betyr at planen og implementasjonen traff bedre første gang.',
         rounds, lambda v: f'{v:.0f}'),
        ('gatef', 'Gate F-returer per levert todo', 'Mekaniske returer på V-blokk-formatet. '
         'Null betyr at fix-rundene leverte riktig format uten en ekstra runde.',
         gatef, lambda v: f'{v:.0f}'),
        ('daily', 'Kostnad per dag', 'Kontekst, ikke måltall: r = 0,96 mot antall agentkjøringer per dag, '
         'så den måler hvor mye vi jobbet — ikke hvor effektivt. Den utløser derfor ingen '
         '§8c-plikt. Les den sammen med de tre over, aldri alene.',
         daily, lambda v: f'{v:,.1f} cr'),
    ]
    n_ms = len(ms_pts)
    ms_txt = ('uten tiltaksmarkører i dette vinduet' if not n_ms else
              f'med {n_ms} tiltak markert' if n_ms > 1 else 'med ett tiltak markert')
    h = [f'<section><h2>Trend</h2><p class="lede">Retningen over tid, {ms_txt}. '
         'Alle fire kurvene er «lavere er bedre». Pilen sammenligner snittet av de siste punktene '
         'mot de like mange før — den vises ikke før det finnes minst tre på hver side, fordi en '
         'retning utledet av to punkter er støy.</p><div class="tgrid">']
    for key, title, lede, pts, fmt_y in cards:
        is_gate = SERIES[key][1]
        h.append(f'<div class="tcard"><h3>{esc(title)}</h3><p class="t-lede">{esc(lede)}</p>'
                 f'{sparkline(pts, fmt_y, ms_pts, is_gate=is_gate)}</div>')
    h.append('</div></section>')
    return '\n'.join(h)


def normalize(rows, rl):
    """Tilordner rolle og oppretter todo-nummeret. Muterer `rows`, og er IDEMPOTENT.

    Trukket ut av `render` fordi `trend_report` gjorde en enklere variant selv: den hoppet
    over PR→todo-mappingen, og samme måling kom ut som -13 % på tekstsiden og -34 % i
    grafen. To kilder til ett tall er en vakt som kan være grønn mens virkeligheten er rød.
    """
    if rows and rows[0].get('_normalized'):
        return
    # PR-nummer → todo via run-log; «12A» → «12» når delleveransen ikke har egen run-log-rad
    # men hovedtodoen har aktivitet.
    pr_to_todo = {v['pr']: k for k, v in rl.items() if v.get('pr')}
    keys = {r['todo'] for r in rows}
    for r in rows:
        r['role'] = role(r.get('type'))
        t = pr_to_todo.get(r['todo'], r['todo'])
        if re.fullmatch(r'\d+[A-Z]', t) and t not in rl and t[:-1] in keys:
            t = t[:-1]
        r['todo'] = t
    for r in rows:
        r['_normalized'] = True


def trend_report(rows, events, since):
    """Tekstversjonen av trend-seksjonen, for §8c. Exit 1 hvis noe går feil vei.

    Deler datauttrekk og dom med `trend_section` — en §8c-kjøring som sier «uendret»
    mens grafen viser oppgang ville vært to kilder til samme sannhet, altså en vakt
    som kan være grønn mens virkeligheten er rød.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    rl = run_log(_loop_doc(here, 'run-log.md'))
    normalize(rows, rl)
    per = _per_todo(rows)
    days, _ = _days(rows, events)

    merged = sorted(((i['ts'], nr, i) for nr, i in rl.items()
                     if i.get('outcome') == 'merged' and i.get('ts') and i['ts'] >= since),
                    key=lambda x: x[0])
    series = {
        SERIES['cost']: [per[nr]['credits'] for _, nr, _ in merged
                         if nr in per and per[nr]['credits'] > 0],
        SERIES['rounds']: [v for _, _, i in merged
                           if (v := _num(i.get('review_rounds'))) is not None],
        SERIES['gatef']: [float(i['gate_f']) for _, _, i in merged
                          if i.get('gate_f') is not None],
        SERIES['daily']: [sum(days[d].values()) for d in sorted(days)],
    }
    worse = []
    print(f'Trend siden {since} — alle målinger: lavere er bedre. Kostnad i AI credits.\n')
    n_merged = len(merged)
    n_cost = len(series[SERIES['cost']])
    if n_merged and n_cost < n_merged:
        print(f'  {NOT_MEASURED}: {n_merged - n_cost} av {n_merged} mergede todoer mangler `credits=` i run-loggen\n')
    for (name, is_gate), vals in series.items():
        v = _verdict(vals)
        if not v:
            print(f'  {name:32s} {len(vals):3d} punkter  — for få til en retning')
            continue
        arrow, cls, txt = v
        flag = {'good': 'OK', 'bad': 'FEIL VEI', 'flat': 'flat'}[cls]
        if not is_gate:
            flag = 'kontekst (utløser ikke §8c)'
        print(f'  {name:32s} {len(vals):3d} punkter  {arrow} {txt:34s} {flag}')
        if cls == 'bad' and is_gate:
            worse.append((name, txt))
    if worse:
        print('\n§8c-HANDLING (måletall): ' + '; '.join(f'«{n}» {t}' for n, t in worse))
        print('  Finn årsaken, innfør et tiltak ELLER logg i decision-log hvorfor ikke.')
        return 1
    print('\nIngen måling går feil vei. Ingen §8c-handling på tallsiden.')
    return 0


def render(path, rows, events, since, cutover):
    here = os.path.dirname(os.path.abspath(__file__))
    rl = run_log(_loop_doc(here, 'run-log.md'))
    coord = coordinator_calls(events)
    ms = milestones(here)

    normalize(rows, rl)
    per = _per_todo(rows)

    # ---- Totaler ----
    total = cr_sum(u['credits'] for u in events)
    tot_coord = cr_sum(c[1] for c in coord)
    in_window = {nr for nr, i in rl.items() if i.get('ts') and i['ts'] >= since}
    todo_nrs = set(per) | in_window
    merged = [n for n in todo_nrs if rl.get(n, {}).get('outcome') == 'merged']
    merged_cr = [per[n]['credits'] for n in merged if n in per]

    # ---- Per dag, stablet per rolle ----
    days, day_src = _days(rows, events)
    day_keys = sorted(days)
    day_max = max((sum(days[d].values()) for d in day_keys), default=1) or 1

    # ---- Per rolle/modell (bare hendelser) ----
    rm = defaultdict(lambda: {'n': 0, 'credits': None, 'out': 0})
    for u in events:
        k = (role(u.get('agent')), model_short(u['model']))
        rm[k]['n'] += 1; rm[k]['out'] += u['out']
        if u['credits'] is not None:
            rm[k]['credits'] = (rm[k]['credits'] or 0.0) + u['credits']
    rm_max = max((v['credits'] or 0 for v in rm.values()), default=1) or 1

    # ---- Før/etter kostnadsgrepene ----
    def split(items, ts=lambda x: x['ts']):
        return [x for x in items if ts(x) < cutover], [x for x in items if ts(x) >= cutover]

    def per_call(us):
        vals = [u['credits'] for u in us if u['credits'] is not None]
        return (sum(vals) / len(vals)) if vals else None

    metrics = []
    todo_t = sorted((rl[n]['ts'], per[n]['credits']) for n in merged if n in per and rl[n].get('ts'))
    tb = [c for t, c in todo_t if t < cutover]; ta = [c for t, c in todo_t if t >= cutover]
    metrics.append(('Credits per levert todo (run-log)', sum(tb) / len(tb) if tb else None,
                    sum(ta) / len(ta) if ta else None, len(tb), len(ta), 'money', 'lower'))
    for key, label in (('planner', 'Planner, credits per kall'), ('implementer', 'Implementer, credits per kall'),
                       ('planreview', 'Plan-review, credits per kall'),
                       ('kodereview', 'Kode-review inkl. linser, credits per kall')):
        b, a = split([u for u in events if role(u.get('agent')) == key])
        metrics.append((label, per_call(b), per_call(a), len(b), len(a), 'money', 'lower'))
    sb, sa = split([u for u in events if role(u.get('agent')) == 'scout'])
    wb, wa = split([u for u in events if role(u.get('agent')) in ('planner', 'implementer')])
    metrics.append(('Scout-kall per planner/implementer-kall',
                    len(sb) / len(wb) if wb else None, len(sa) / len(wa) if wa else None,
                    len(wb), len(wa), 'num', 'higher'))
    cb = [c for c in coord if c[0] < cutover]; ca = [c for c in coord if c[0] >= cutover]
    metrics.append(('Koordinator, snittkontekst per kall',
                    (sum(c[2] for c in cb) / len(cb)) if cb else None,
                    (sum(c[2] for c in ca) / len(ca)) if ca else None, len(cb), len(ca), 'ktok', 'lower'))
    cbm = [c[1] for c in cb if c[1] is not None]; cam = [c[1] for c in ca if c[1] is not None]
    metrics.append(('Koordinator, credits per kall',
                    (sum(cbm) / len(cbm)) if cbm else None,
                    (sum(cam) / len(cam)) if cam else None, len(cbm), len(cam), 'money', 'lower'))
    gf_b = [rl[n]['gate_f'] for n in merged if rl[n].get('ts', '') < cutover and rl[n].get('gate_f') is not None]
    gf_a = [rl[n]['gate_f'] for n in merged if rl[n].get('ts', '') >= cutover and rl[n].get('gate_f') is not None]
    metrics.append(('Gate F-returer per levert todo', sum(gf_b) / len(gf_b) if gf_b else None,
                    sum(gf_a) / len(gf_a) if gf_a else None, len(gf_b), len(gf_a), 'num', 'lower'))

    def fmtv(v, kind):
        if v is None:
            return '<span class="nil">–</span>'
        if kind == 'money':
            return money(v)
        if kind == 'ktok':
            return f'{v / 1000:,.0f}k'
        return f'{v:.2f}'

    def delta(b, a, better, nb, na):
        if b is None or a is None or b == 0 or nb < 3 or na < 3:
            return '<span class="chip nil">for lite data</span>'
        pct = (a - b) / b * 100
        good = (pct < 0) if better == 'lower' else (pct > 0)
        cls = 'good' if good else ('flat' if abs(pct) < 5 else 'bad')
        return f'<span class="chip {cls}">{pct:+.0f} %</span>'

    # ---- Per todo ----
    def last_of(nr):
        return max(per[nr]['last'] if nr in per else '', rl.get(nr, {}).get('ts', ''))
    todo_rows = sorted(todo_nrs, key=last_of, reverse=True)[:30]

    # ---- HTML ----
    now = datetime.now(OSLO).strftime('%Y-%m-%d %H:%M')
    h = []
    h.append('<title>Loop-målinger</title>')
    h.append('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">')
    h.append('<style>' + CSS + '</style>')
    h.append('<main>')
    h.append('<header><p class="eyebrow">{{PROJECT_NAME}} · orkestreringsloopen</p><h1>Loop-målinger</h1>')
    h.append(f'<div class="meta"><span>Generert {esc(now)}</span><span>Siden {esc(since[:16])}</span>'
             f'<span>Grepene fra {esc(local(cutover).strftime("%d.%m %H:%M"))}</span>'
             f'<span>Enhet: AI credits (assistant.usage <code>cost</code> / <code>/usage</code>)</span></div></header>')

    h.append('<section class="kpis">')
    for label, val, sub in (
        ('Total kostnad (økter)', money(total),
         f'{len(events):,} kall med assistant.usage' if events else 'ingen assistant.usage i øktloggene — se per todo'),
        ('Koordinator', money(tot_coord),
         f'{tot_coord / total * 100:.0f} % av totalen' if total and tot_coord is not None else ''),
        ('Levert (merget)', str(len(merged)), f'av {len(todo_nrs)} todos med aktivitet'),
        ('Per levert todo', money(sum(merged_cr) / len(merged_cr)) if merged_cr else NOT_MEASURED,
         f'`credits=` i run-loggen, {len(merged_cr)} av {len(merged)} mergede har tall'),
    ):
        h.append(f'<div class="kpi"><div class="k-label">{esc(label)}</div><div class="k-val">{esc(val)}</div><div class="k-sub">{esc(sub)}</div></div>')
    h.append('</section>')

    h.append(trend_section(per, rl, days, day_keys, since, ms_points(ms)))
    h.append(tiltak_section(ms))
    h.append('<section><h2>Virker kostnadsgrepene?</h2><p class="lede">Før og etter at grepene ble innført. '
             'n = antall kall eller todos bak snittet. Grønn betyr bedring. Endring vises først når begge sider har minst 3 datapunkter.</p>')
    h.append('<div class="scroll"><table class="cmp"><thead><tr><th>Mål</th><th class="num">Før</th><th class="num">Etter</th><th>Endring</th><th class="num">n før / etter</th></tr></thead><tbody>')
    for label, b, a, nb, na, kind, better in metrics:
        h.append(f'<tr><td>{esc(label)}</td><td class="num">{fmtv(b, kind)}</td><td class="num">{fmtv(a, kind)}</td>'
                 f'<td>{delta(b, a, better, nb, na)}</td><td class="num muted">{nb} / {na}</td></tr>')
    h.append('</tbody></table></div></section>')

    h.append(effort_section(per, coord, rl, cutover))
    src_txt = ('fra assistant.usage per rolle' if day_src == 'assistant.usage'
               else 'fra `credits=` i run-loggen, ført på dagen raden ble skrevet')
    h.append(f'<section><h2>Kostnad per dag</h2><p class="lede">AI credits {esc(src_txt)}.</p><div class="legend">')
    used = {k for d in day_keys for k, v in days[d].items() if v > 0}
    for k, name, var in ROLES:
        if k in used:
            h.append(f'<span><i style="background:var({var})"></i>{esc(name)}</span>')
    h.append('</div><div class="days">')
    if not day_keys:
        h.append(f'<p class="muted">{NOT_MEASURED}: ingen credits i vinduet.</p>')
    for d in day_keys:
        tot = sum(days[d].values())
        segs = ''.join(
            f'<span style="width:{days[d][k] / day_max * 100:.2f}%;background:var({var})" title="{esc(name)} {money(days[d][k])}"></span>'
            for k, name, var in ROLES if days[d][k] > 0)
        h.append(f'<div class="day"><span class="d-lbl mono">{esc(d[5:])}</span><span class="bar">{segs}</span><span class="d-val num">{money(tot)}</span></div>')
    h.append('</div></section>')

    h.append('<section><h2>Per rolle og modell</h2><p class="lede">Fra assistant.usage-hendelsene. '
             'Uten hendelser er tabellen tom: <code>/usage</code> gir bare totaler per økt.</p>'
             '<div class="scroll"><table><thead><tr><th>Rolle</th><th>Modell</th>'
             '<th class="num">Kall</th><th class="num">Credits totalt</th><th class="num">Credits per kall</th><th class="w">Andel</th></tr></thead><tbody>')
    order = {k: i for i, (k, _, _) in enumerate(ROLES)}
    names = {k: (n, v) for k, n, v in ROLES}
    for (rk, m), v in sorted(rm.items(), key=lambda x: (order[x[0][0]], -(x[1]['credits'] or 0))):
        name, var = names[rk]
        per_txt = '–' if v['credits'] is None or not v['n'] else money(v['credits'] / v['n'])
        h.append(f'<tr><td><i class="dot" style="background:var({var})"></i>{esc(name)}</td><td>{esc(m)}</td><td class="num">{v["n"]:,}</td>'
                 f'<td class="num">{money(v["credits"])}</td><td class="num">{per_txt}</td>'
                 f'<td class="w"><span class="hbar" style="width:{(v["credits"] or 0) / rm_max * 100:.1f}%;background:var({var})"></span></td></tr>')
    h.append('</tbody></table></div></section>')

    h.append('<section><h2>Per todo</h2><p class="lede">Siste 30 etter aktivitet. Credits er summen av '
             '<code>credits=</code> i run-loggen; koordinatorens kall er med i tallet når det er hentet fra '
             '<code>/usage</code> for todoen.</p>'
             '<div class="scroll"><table><thead><tr><th>Todo</th><th>Sist aktiv</th>'
             '<th class="num">Credits</th><th class="num">Gate F</th><th class="num">Review-runder</th><th>Utfall</th></tr></thead><tbody>')
    for nr in todo_rows:
        info = rl.get(nr, {})
        oc = info.get('outcome', '')
        pill = f'<span class="pill {"ok" if oc == "merged" else "wip"}">{esc(oc or "pågår")}</span>'
        gf = info.get('gate_f')
        last = last_of(nr)
        h.append(f'<tr><td class="mono">{esc(nr)}</td><td class="muted">{esc(local(last).strftime("%d.%m %H:%M")) if last else "–"}</td>'
                 f'<td class="num strong">{money(per[nr]["credits"] if nr in per else None)}</td>'
                 f'<td class="num">{"–" if gf is None else gf}</td><td class="num">{esc(info.get("review_rounds", "–"))}</td><td>{pill}</td></tr>')
    h.append('</tbody></table></div></section>')
    h.append('<footer class="muted">Generert av <code>python3 tasks/measure-cost.py &lt;since&gt; --html &lt;sti&gt;</code>. '
             'assistant.usage dedupliseres per id. Et tall uten kilde står som IKKE MÅLT, aldri som 0.</footer></main>')
    open(path, 'w', encoding='utf-8').write('\n'.join(h) + '\n')


def effort_section(per, coord, rl, cutover):
    """Koordinator-effort: medium → high og high før/etter kostnadsgrepene.

    Periodene avgrenses av når effort-verdien (`reasoningEffort` i assistant.usage) skifter, ikke av
    en hardkodet dato. Todos tilordnes perioden merge-raden i run-loggen ble skrevet i. Sammenligningen
    er ikke kontrollert: andre endringer (V-blokk-krav, kostnadsgrep) skjedde samtidig, og utvalgene er
    små. Uten effort i hendelsene vises ikke seksjonen.
    """
    mediums = sorted(c[0] for c in coord if c[4] == 'medium')
    if not mediums:
        return ''
    highs = sorted(c[0] for c in coord if c[4] == 'high' and c[0] > mediums[-1])
    if not highs:
        return ''
    switch = highs[0]  # første high etter siste medium
    periods = [('Medium', mediums[0], switch), ('High, før grepene', switch, cutover), ('High, etter grepene', cutover, None)]

    def inside(ts, a, b):
        return (a is None or ts >= a) and (b is None or ts < b)

    cols = []
    for name, a, b in periods:
        cs = [c for c in coord if inside(c[0], a, b)]
        hours = len({local(c[0]).strftime('%Y-%m-%d %H') for c in cs})
        todos = [n for n, i in rl.items() if i.get('outcome') == 'merged' and i.get('ts') and inside(i['ts'], a, b)]
        gf = [rl[n]['gate_f'] for n in todos if rl[n].get('gate_f') is not None]
        rr = [int(rl[n]['review_rounds']) for n in todos if str(rl[n].get('review_rounds', '')).isdigit()]
        pr = [int(rl[n]['plan_rounds']) for n in todos if str(rl[n].get('plan_rounds', '')).isdigit()]
        cvals = [c[1] for c in cs if c[1] is not None]
        tcr = [per[n]['credits'] for n in todos if n in per]
        cols.append({
            'name': name,
            'span': (local(a).strftime('%d.%m %H:%M') if a else 'start') + ' – ' + (local(b).strftime('%d.%m %H:%M') if b else 'nå'),
            'Kall': f'{len(cs):,}',
            'Aktive timer': str(hours),
            'Koordinator credits totalt': money(sum(cvals)) if cvals else NOT_MEASURED,
            'Credits per kall': money(sum(cvals) / len(cvals)) if cvals else '–',
            'Output per kall (inkl. tenking)': f'{sum(c[5] for c in cs) / len(cs):,.0f}' if cs else '–',
            'Snittkontekst per kall': f'{sum(c[2] for c in cs) / len(cs) / 1000:,.0f}k' if cs else '–',
            'Kall per aktive time': f'{len(cs) / hours:,.0f}' if hours else '–',
            'Leverte todos (merget her)': str(len(todos)),
            'Credits per levert todo': money(sum(tcr) / len(tcr)) if tcr else '–',
            'Gate F-returer per todo': f'{sum(gf) / len(gf):.2f}' if gf else '–',
            'Plan-runder per todo': f'{sum(pr) / len(pr):.1f}' if pr else '–',
            'Kode-review-runder per todo': f'{sum(rr) / len(rr):.1f}' if rr else '–',
        })
    keys = [k for k in cols[0] if k not in ('name', 'span')]
    h = ['<section><h2>Koordinator-effort: medium mot high</h2>',
         f'<p class="lede">Effort ble satt fra medium til high {esc(local(switch).strftime("%d.%m kl. %H:%M"))} (fra øktloggen). '
         'Periodene nedenfor er ikke kontrollerte forsøk: V-blokk-kravet og kostnadsgrepene kom i samme tidsrom, og utvalgene er små. '
         'Tolk kvalitetsradene (Gate F og runder) som retning, ikke som bevis.</p>',
         '<div class="scroll"><table><thead><tr><th>Mål</th>']
    for c in cols:
        h.append(f'<th class="num">{esc(c["name"])}<br><span class="muted mono" style="font-weight:400">{esc(c["span"])}</span></th>')
    h.append('</tr></thead><tbody>')
    for k in keys:
        h.append(f'<tr><td>{esc(k)}</td>' + ''.join(f'<td class="num">{esc(c[k])}</td>' for c in cols) + '</tr>')
    h.append('</tbody></table></div></section>')
    return ''.join(h)


CSS = '''
:root{
  --bg:#F6F7F4;--surface:#FFFFFF;--sunk:#EFF1EC;--ink:#1D2320;--muted:#5E6862;--faint:#8A948D;
  --line:#D9DED8;--line-soft:#E7EAE4;--accent:#0F6E6E;
  --good-bg:#E3F2E9;--good-ink:#1F7F4F;--bad-bg:#F4E0DA;--bad-ink:#8A3B2E;--flat-bg:#E9EBE7;--flat-ink:#6B7369;
  --c-koord:#6B7A8F;--c-plan:#5B4B9E;--c-preview:#9C8FD0;--c-impl:#0F6E6E;--c-review:#A8541F;--c-scout:#4E9F6A;--c-annet:#B8BFB9;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#14181A;--surface:#1C2124;--sunk:#191E20;--ink:#E4E8E3;--muted:#9AA59D;--faint:#6F7A73;
  --line:#2E3538;--line-soft:#242A2D;--accent:#4FB3B0;
  --good-bg:#1B3327;--good-ink:#6FCB95;--bad-bg:#3B221D;--bad-ink:#E5917F;--flat-bg:#242A26;--flat-ink:#8D978F;
  --c-koord:#9BAAB9;--c-plan:#B3A6EA;--c-preview:#7C70B0;--c-impl:#4FB3B0;--c-review:#E0A472;--c-scout:#6FCB95;--c-annet:#4A524D;
}}
:root[data-theme="dark"]{
  --bg:#14181A;--surface:#1C2124;--sunk:#191E20;--ink:#E4E8E3;--muted:#9AA59D;--faint:#6F7A73;
  --line:#2E3538;--line-soft:#242A2D;--accent:#4FB3B0;
  --good-bg:#1B3327;--good-ink:#6FCB95;--bad-bg:#3B221D;--bad-ink:#E5917F;--flat-bg:#242A26;--flat-ink:#8D978F;
  --c-koord:#9BAAB9;--c-plan:#B3A6EA;--c-preview:#7C70B0;--c-impl:#4FB3B0;--c-review:#E0A472;--c-scout:#6FCB95;--c-annet:#4A524D;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font:15px/1.5 "IBM Plex Sans",system-ui,-apple-system,sans-serif;margin:0}
main{max-width:1040px;margin:0 auto;padding:26px 18px 72px;display:grid;gap:34px}
.mono,code{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace}
code{font-size:.88em;background:var(--sunk);border:1px solid var(--line-soft);border-radius:4px;padding:0 4px}
.eyebrow{margin:0 0 4px;font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint)}
h1{font-size:27px;font-weight:600;letter-spacing:-.015em;margin:0;text-wrap:balance}
h2{font-size:17px;font-weight:600;margin:0 0 6px;text-wrap:balance}
.lede{margin:0 0 12px;color:var(--muted);font-size:13.5px;max-width:65ch}
.meta{color:var(--muted);font-size:12.5px;display:flex;flex-wrap:wrap;gap:4px 16px;margin-top:7px}
.muted{color:var(--muted)}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.strong{font-weight:600}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.kpi{background:var(--surface);border:1px solid var(--line-soft);border-radius:8px;padding:14px 16px}
.k-label{font-size:12px;color:var(--muted);letter-spacing:.02em}
.k-val{font-size:26px;font-weight:600;font-variant-numeric:tabular-nums;margin:2px 0}
.k-sub{font-size:12px;color:var(--faint)}
.scroll{overflow-x:auto;border:1px solid var(--line-soft);border-radius:8px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th{font-weight:500;font-size:12px;color:var(--muted);text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:8px 12px;border-bottom:1px solid var(--line-soft);vertical-align:middle}
tbody tr:last-child td{border-bottom:0}
th.num{text-align:right}
.w{width:26%;min-width:120px}
.hbar{display:block;height:8px;border-radius:2px;min-width:2px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px;vertical-align:0}
.chip{display:inline-block;font-size:12px;font-weight:500;padding:1px 8px;border-radius:999px;font-variant-numeric:tabular-nums}
.chip.good{background:var(--good-bg);color:var(--good-ink)}
.chip.bad{background:var(--bad-bg);color:var(--bad-ink)}
.chip.flat,.chip.nil{background:var(--flat-bg);color:var(--flat-ink)}
.nil{color:var(--faint)}
.pill{font-size:12px;padding:1px 8px;border-radius:999px}
.pill.ok{background:var(--good-bg);color:var(--good-ink)}
.pill.wip{background:var(--flat-bg);color:var(--flat-ink)}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12.5px;color:var(--muted);margin:4px 0 12px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.days{display:grid;gap:6px;background:var(--surface);border:1px solid var(--line-soft);border-radius:8px;padding:14px 16px}
.day{display:grid;grid-template-columns:52px 1fr 72px;align-items:center;gap:12px;font-size:13px}
.d-lbl{color:var(--muted);font-size:12px}
.bar{display:flex;height:14px;background:var(--sunk);border-radius:3px;overflow:hidden}
.bar span{display:block;height:100%}
footer{font-size:12px}
h3{font-size:14px;font-weight:600;margin:0 0 3px}
.tgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.tcard{background:var(--surface);border:1px solid var(--line-soft);border-radius:8px;padding:14px 16px}
.t-lede{margin:0 0 10px;color:var(--muted);font-size:12.5px;line-height:1.45}
.sp-wrap{display:grid;gap:8px}
.sp{width:100%;height:96px;display:block;overflow:visible}
.sp-line{fill:none;stroke:var(--accent);stroke-width:1.8;stroke-linejoin:round;stroke-linecap:round;vector-effect:non-scaling-stroke}
.sp-area{fill:var(--accent);opacity:.09}
.sp-dot{fill:var(--surface);stroke:var(--accent);stroke-width:1.4;vector-effect:non-scaling-stroke}
.ms{stroke:var(--faint);stroke-width:1;stroke-dasharray:3 3;vector-effect:non-scaling-stroke}
.ms-t{fill:var(--faint);font-size:9px;font-family:"IBM Plex Mono",monospace}
.sp-foot{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;font-size:12px}
@media (max-width:520px){.sp{height:112px}}
.tl{display:grid;gap:2px;background:var(--surface);border:1px solid var(--line-soft);border-radius:8px;padding:6px 0}
.tl-row{display:grid;grid-template-columns:118px 1fr;gap:14px;padding:11px 16px;border-bottom:1px solid var(--line-soft)}
.tl-row:last-child{border-bottom:0}
.tl-when{color:var(--muted);font-size:12px;padding-top:2px;white-space:nowrap}
.tl-head{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline}
.tl-head strong{font-weight:600;font-size:13.5px}
.tl-body{margin:4px 0 0;color:var(--muted);font-size:12.5px;line-height:1.5}
.tag{font-size:11px;padding:1px 7px;border-radius:999px;white-space:nowrap}
.tag.auto{background:var(--good-bg);color:var(--good-ink)}
.tag.owner{background:var(--flat-bg);color:var(--flat-ink)}
.tag.ext{background:var(--bad-bg);color:var(--bad-ink)}
@media (max-width:520px){.tl-row{grid-template-columns:1fr;gap:2px}}
'''
