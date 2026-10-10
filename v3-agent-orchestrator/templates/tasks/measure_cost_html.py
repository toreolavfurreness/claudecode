"""HTML-målesiden for loopen (kalles av tasks/measure-cost.py --html <sti>).

Kilder: subagent-radene fra measure-cost.py, koordinatorens egne kall (sesjonens hoved-jsonl) og
docs/superpowers/loop/run-log.md (Gate F-returer, review-runder, utfall). Siden er avledet — rediger
aldri HTML-en for hånd; den committes ikke (kun scratchpad), og publiseres på fast artifact-lenke.
"""
import html, json, os, re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

OSLO = ZoneInfo('Europe/Oslo')
ROLES = [  # (nøkkel, visningsnavn, CSS-variabel)
    ('koordinator', 'Koordinator', '--c-koord'),
    ('planner', 'Planner', '--c-plan'),
    ('planreview', 'Plan-review', '--c-preview'),
    ('implementer', 'Implementer', '--c-impl'),
    ('kodereview', 'Kode-review + linser', '--c-review'),
    ('scout', 'Scout', '--c-scout'),
    ('annet', 'Annet', '--c-annet'),
]
ROLE_OF = {
    '{{PROJECT_NAME}}-planner': 'planner', '{{PROJECT_NAME}}-reviewer': 'planreview',
    '{{PROJECT_NAME}}-implementer': 'implementer', '{{PROJECT_NAME}}-code-reviewer': 'kodereview',
    'rls-migration-reviewer': 'kodereview', 'race-reviewer': 'kodereview',
    'ios-design-reviewer': 'kodereview', 'edge-function-reviewer': 'kodereview',
    '{{PROJECT_NAME}}-scout': 'scout',
}


def role(t):
    return ROLE_OF.get(t, 'annet')


def local(ts):
    d = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    if d.tzinfo is None:  # tidsstempler uten sone (f.eks. --cutover) er UTC, som transkriptene
        d = d.replace(tzinfo=ZoneInfo('UTC'))
    return d.astimezone(OSLO)


def model_short(m):
    m = m or ''
    for k, v in (('opus-5-5', 'Opus 5.5'), ('opus', 'Opus'), ('sonnet', 'Sonnet'), ('haiku', 'Haiku'), ('fable', 'Fable')):
        if k in m:
            return v
    return m or '?'


def coordinator_calls(dirs, since, usd):
    """Én rad per unikt hovedsløyfe-kall: (ts, usd, kontekst-tokens, modell, effort, output-tokens)."""
    out = []
    for d in dirs:
        f = d.rstrip('/') + '.jsonl'
        if not os.path.exists(f):
            continue
        seen = {}
        for line in open(f, encoding='utf-8', errors='replace'):
            try:
                e = json.loads(line)
            except Exception:
                continue
            msg = e.get('message') or {}
            u = msg.get('usage') if isinstance(msg, dict) else None
            ts = e.get('timestamp')
            if not u or not ts or ts < since or e.get('isSidechain'):
                continue
            seen[msg.get('id') or id(e)] = (ts, u, msg.get('model', '?'), e.get('effort') or '?')
        for ts, u, m, ef in seen.values():
            ctx = (u.get('input_tokens') or 0) + (u.get('cache_creation_input_tokens') or 0) + (u.get('cache_read_input_tokens') or 0)
            out.append((ts, usd(u, m), ctx, m, ef, u.get('output_tokens') or 0))
    return out


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
    return f'${x:,.0f}' if x >= 100 else f'${x:,.2f}'


# Tiltak uten egen decision-log-rad: (tidspunkt, tittel, tekst, kilde). Tom som standard.
EXTRA_MILESTONES = []

# Rader i decision-log som er TILTAK på loopen selv, ikke beslutninger om én todo.
MEASURE_ROW = re.compile(
    r'^### (\d{4}-\d\d-\d\d) (\d\d:\d\d) — (§8c \[B\]|\[kostnadsgrep\]|\[modellbytte\]|\[tiltak\]|§6c[^:]*\[B\]):\s*(.+)$')


def milestones(here):
    """Tiltakene, lest fra decision-log — ÉN kilde for både grafmarkørene og tiltakslista.

    Hardkodet liste var forrige form. Den ville drevet fra loggen i det et tiltak ble
    innført uten at noen husket å oppdatere grafen, og markøren ville da pekt på et
    tidspunkt uten hendelse mens den ekte hendelsen var usynlig.
    """
    path = os.path.join(here, '..', 'docs', 'superpowers', 'loop', 'decision-log.md')
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


def trend_section(per, rl, days, day_keys, since, ms_pts):
    """Fire tidsserier. Alle fire er «lavere er bedre».

    ALLE seriene filtreres på `since`. Uten det filteret arvet runde- og Gate F-seriene
    hele run-loggens historikk (105 punkter) mens kostnadsserien var begrenset til
    perioden med agentdata (27) — to kurver ved siden av hverandre som dekker ulike
    tidsrom, uten at noe i bildet sier fra.
    """
    merged = sorted(
        ((info['ts'], nr, info) for nr, info in rl.items()
         if info.get('outcome') == 'merged' and info.get('ts') and info['ts'] >= since),
        key=lambda x: x[0])

    cost = [(ts, per[nr]['usd'], f'TODO {nr}') for ts, nr, _ in merged
            if nr in per and per[nr]['usd'] > 0]
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
        ('cost', 'Kostnad per levert todo', 'Agentkostnad per merget todo, i mergerekkefølge. '
         'Koordinatorkostnaden er ikke fordelt per todo.', cost, lambda v: f'${v:,.0f}'),
        ('rounds', 'Kode-review-runder per levert todo', 'Hvor mange runder koden måtte gjennom før merge. '
         'Færre runder betyr at planen og implementasjonen traff bedre første gang.',
         rounds, lambda v: f'{v:.0f}'),
        ('gatef', 'Gate F-returer per levert todo', 'Mekaniske returer på V-blokk-formatet. '
         'Null betyr at fix-rundene leverte riktig format uten en ekstra runde.',
         gatef, lambda v: f'{v:.0f}'),
        ('daily', 'Kostnad per dag', 'Kontekst, ikke måltall: r = 0,96 mot antall agentkjøringer per dag, '
         'så den måler hvor mye vi jobbet — ikke hvor effektivt. Den utløser derfor ingen '
         '§8c-plikt. Les den sammen med de tre over, aldri alene.',
         daily, lambda v: f'${v:,.0f}'),
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
    # PR-nummer (fra «Kode-review PR 12»-beskrivelser) → todo via run-log; «12A» → «12» når
    # delleveransen ikke har egen run-log-rad men hovedtodoen har aktivitet.
    pr_to_todo = {v['pr']: k for k, v in rl.items() if v.get('pr')}
    keys = {r['todo'] for r in rows}
    for r in rows:
        r['role'] = role(r['type'])
        t = pr_to_todo.get(r['todo'], r['todo'])
        if re.fullmatch(r'\d+[A-Z]', t) and t not in rl and t[:-1] in keys:
            t = t[:-1]
        r['todo'] = t
    # Linse-agenter beskrives ofte med PR-nummeret («Race review PR 12»). Er PR-en ikke i run-log
    # ennå, arver de forelderens todo (kode-revieweren navngir todoen).
    by_id = {r['agent']: r for r in rows}
    for r in rows:
        p = by_id.get(r['parent'])
        if p and re.fullmatch(r'\d{3,4}', r['todo']) and int(r['todo']) >= 500 and p['todo'] != r['todo']:
            r['todo'] = p['todo']
    for r in rows:
        r['_normalized'] = True


def trend_report(rows, dirs, since, usd):
    """Tekstversjonen av trend-seksjonen, for §8c. Exit 1 hvis noe går feil vei.

    Deler datauttrekk og dom med `trend_section` — en §8c-kjøring som sier «uendret»
    mens grafen viser oppgang ville vært to kilder til samme sannhet, altså en vakt
    som kan være grønn mens virkeligheten er rød.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    rl = run_log(os.path.join(here, '..', 'docs', 'superpowers', 'loop', 'run-log.md'))
    coord = coordinator_calls(dirs, since, usd)
    normalize(rows, rl)
    per = defaultdict(lambda: {'usd': 0.0})
    for r in rows:
        if r['todo'] != '-':
            per[r['todo']]['usd'] += r['usd']
    days = defaultdict(lambda: defaultdict(float))
    for r in rows:
        days[local(r['t0']).strftime('%Y-%m-%d')][r['role']] += r['usd']
    for ts, u, *_ in coord:
        days[local(ts).strftime('%Y-%m-%d')]['koordinator'] += u

    merged = sorted(((i['ts'], nr, i) for nr, i in rl.items()
                     if i.get('outcome') == 'merged' and i.get('ts') and i['ts'] >= since),
                    key=lambda x: x[0])
    series = {
        SERIES['cost']: [per[nr]['usd'] for _, nr, _ in merged
                         if nr in per and per[nr]['usd'] > 0],
        SERIES['rounds']: [v for _, _, i in merged
                           if (v := _num(i.get('review_rounds'))) is not None],
        SERIES['gatef']: [float(i['gate_f']) for _, _, i in merged
                          if i.get('gate_f') is not None],
        SERIES['daily']: [sum(days[d].values()) for d in sorted(days)],
    }
    worse = []
    print(f'Trend siden {since} — alle målinger: lavere er bedre.\n')
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


def render(path, rows, dirs, since, cutover, usd):
    here = os.path.dirname(os.path.abspath(__file__))
    rl = run_log(os.path.join(here, '..', 'docs', 'superpowers', 'loop', 'run-log.md'))
    coord = coordinator_calls(dirs, since, usd)
    ms = milestones(here)

    normalize(rows, rl)

    # ---- Totaler ----
    tot_agents = sum(r['usd'] for r in rows)
    tot_coord = sum(c[1] for c in coord)
    total = tot_agents + tot_coord
    todo_nrs = {r['todo'] for r in rows if r['todo'] != '-'}
    merged = [n for n in todo_nrs if rl.get(n, {}).get('outcome') == 'merged']

    # ---- Per dag, stablet per rolle ----
    days = defaultdict(lambda: defaultdict(float))
    for r in rows:
        days[local(r['t0']).strftime('%Y-%m-%d')][r['role']] += r['usd']
    for ts, u, *_ in coord:
        days[local(ts).strftime('%Y-%m-%d')]['koordinator'] += u
    day_keys = sorted(days)
    day_max = max((sum(days[d].values()) for d in day_keys), default=1) or 1

    # ---- Per rolle/modell ----
    rm = defaultdict(lambda: {'n': 0, 'usd': 0.0, 'out': 0})
    for r in rows:
        k = (r['role'], model_short(r['model']))
        rm[k]['n'] += 1; rm[k]['usd'] += r['usd']; rm[k]['out'] += r['out']
    for _, u, _, m, *_ in coord:
        k = ('koordinator', model_short(m))
        rm[k]['usd'] += u
    coord_calls_n = len(coord)
    rm_max = max((v['usd'] for v in rm.values()), default=1) or 1

    # ---- Før/etter kostnadsgrepene ----
    def split(pred_rows):
        b = [r for r in pred_rows if r['t0'] < cutover]
        a = [r for r in pred_rows if r['t0'] >= cutover]
        return b, a

    def per_run(rs):
        return (sum(r['usd'] for r in rs) / len(rs)) if rs else None

    metrics = []
    for key, label in (('planner', 'Planner, $ per kjøring'), ('implementer', 'Implementer, $ per kjøring'),
                       ('planreview', 'Plan-review, $ per kjøring')):
        b, a = split([r for r in rows if r['role'] == key])
        metrics.append((label, per_run(b), per_run(a), len(b), len(a), 'money', 'lower'))
    b_cr, a_cr = split([r for r in rows if r['type'] == '{{PROJECT_NAME}}-code-reviewer'])
    lens_b, lens_a = split([r for r in rows if r['role'] == 'kodereview'])
    metrics.append(('Kode-review inkl. linser, $ per runde',
                    (sum(r['usd'] for r in lens_b) / len(b_cr)) if b_cr else None,
                    (sum(r['usd'] for r in lens_a) / len(a_cr)) if a_cr else None,
                    len(b_cr), len(a_cr), 'money', 'lower'))
    sb, sa = split([r for r in rows if r['role'] == 'scout'])
    wb, wa = split([r for r in rows if r['role'] in ('planner', 'implementer')])
    metrics.append(('Scout-kall per planner/implementer-kjøring',
                    len(sb) / len(wb) if wb else None, len(sa) / len(wa) if wa else None,
                    len(wb), len(wa), 'num', 'higher'))
    cb = [c for c in coord if c[0] < cutover]; ca = [c for c in coord if c[0] >= cutover]
    metrics.append(('Koordinator, snittkontekst per kall',
                    (sum(c[2] for c in cb) / len(cb)) if cb else None,
                    (sum(c[2] for c in ca) / len(ca)) if ca else None, len(cb), len(ca), 'ktok', 'lower'))
    metrics.append(('Koordinator, $ per kall',
                    (sum(c[1] for c in cb) / len(cb)) if cb else None,
                    (sum(c[1] for c in ca) / len(ca)) if ca else None, len(cb), len(ca), 'money', 'lower'))
    impl_start = {}
    for r in rows:
        if r['role'] == 'implementer' and r['todo'] != '-':
            impl_start[r['todo']] = min(impl_start.get(r['todo'], r['t0']), r['t0'])
    gf_b = [rl[n]['gate_f'] for n, t in impl_start.items() if t < cutover and rl.get(n, {}).get('gate_f') is not None]
    gf_a = [rl[n]['gate_f'] for n, t in impl_start.items() if t >= cutover and rl.get(n, {}).get('gate_f') is not None]
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
    per = defaultdict(lambda: {'plan': 0.0, 'impl': 0.0, 'rev': 0.0, 'scout': 0, 'usd': 0.0, 'last': ''})
    for r in rows:
        if r['todo'] == '-':
            continue
        p = per[r['todo']]
        p['usd'] += r['usd']; p['last'] = max(p['last'], r['t1'] or r['t0'])
        if r['role'] in ('planner', 'planreview'):
            p['plan'] += r['usd']
        elif r['role'] == 'implementer':
            p['impl'] += r['usd']
        elif r['role'] == 'kodereview':
            p['rev'] += r['usd']
        elif r['role'] == 'scout':
            p['scout'] += 1
    todo_rows = sorted(per.items(), key=lambda x: x[1]['last'], reverse=True)[:30]

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
             f'<span>Priser: USD per MTok, platform.claude.com 2026-09-15</span></div></header>')

    h.append('<section class="kpis">')
    for label, val, sub in (
        ('Total kostnad', money(total), f'{len(rows)} agentkjøringer + {coord_calls_n:,} koordinatorkall'),
        ('Koordinator', money(tot_coord), f'{tot_coord / total * 100:.0f} % av totalen' if total else ''),
        ('Levert (merget)', str(len(merged)), f'av {len(todo_nrs)} todos med aktivitet'),
        ('Per levert todo', money(total / len(merged)) if merged else '–', 'total ÷ mergede, inkl. koordinator'),
    ):
        h.append(f'<div class="kpi"><div class="k-label">{esc(label)}</div><div class="k-val">{val}</div><div class="k-sub">{esc(sub)}</div></div>')
    h.append('</section>')

    h.append(trend_section(per, rl, days, day_keys, since, ms_points(ms)))
    h.append(tiltak_section(ms))
    h.append('<section><h2>Virker kostnadsgrepene?</h2><p class="lede">Før og etter at grepene ble innført. '
             'n = antall kjøringer, kall eller todos bak snittet. Grønn betyr bedring. Endring vises først når begge sider har minst 3 datapunkter.</p>')
    h.append('<div class="scroll"><table class="cmp"><thead><tr><th>Mål</th><th class="num">Før</th><th class="num">Etter</th><th>Endring</th><th class="num">n før / etter</th></tr></thead><tbody>')
    for label, b, a, nb, na, kind, better in metrics:
        h.append(f'<tr><td>{esc(label)}</td><td class="num">{fmtv(b, kind)}</td><td class="num">{fmtv(a, kind)}</td>'
                 f'<td>{delta(b, a, better, nb, na)}</td><td class="num muted">{nb} / {na}</td></tr>')
    h.append('</tbody></table></div></section>')

    h.append(effort_section(rows, coord, rl, cutover))
    h.append('<section><h2>Kostnad per dag</h2><div class="legend">')
    for k, name, var in ROLES:
        h.append(f'<span><i style="background:var({var})"></i>{esc(name)}</span>')
    h.append('</div><div class="days">')
    for d in day_keys:
        tot = sum(days[d].values())
        segs = ''.join(
            f'<span style="width:{days[d][k] / day_max * 100:.2f}%;background:var({var})" title="{esc(name)} {money(days[d][k])}"></span>'
            for k, name, var in ROLES if days[d][k] > 0)
        h.append(f'<div class="day"><span class="d-lbl mono">{esc(d[5:])}</span><span class="bar">{segs}</span><span class="d-val num">{money(tot)}</span></div>')
    h.append('</div></section>')

    h.append('<section><h2>Per rolle og modell</h2><div class="scroll"><table><thead><tr><th>Rolle</th><th>Modell</th>'
             '<th class="num">Kjøringer</th><th class="num">$ totalt</th><th class="num">$ per kjøring</th><th class="w">Andel</th></tr></thead><tbody>')
    order = {k: i for i, (k, _, _) in enumerate(ROLES)}
    names = {k: (n, v) for k, n, v in ROLES}
    for (rk, m), v in sorted(rm.items(), key=lambda x: (order[x[0][0]], -x[1]['usd'])):
        name, var = names[rk]
        n_txt = f'{coord_calls_n:,} kall' if rk == 'koordinator' else str(v['n'])
        per_txt = '–' if rk == 'koordinator' or not v['n'] else money(v['usd'] / v['n'])
        h.append(f'<tr><td><i class="dot" style="background:var({var})"></i>{esc(name)}</td><td>{esc(m)}</td><td class="num">{n_txt}</td>'
                 f'<td class="num">{money(v["usd"])}</td><td class="num">{per_txt}</td>'
                 f'<td class="w"><span class="hbar" style="width:{v["usd"] / rm_max * 100:.1f}%;background:var({var})"></span></td></tr>')
    h.append('</tbody></table></div></section>')

    h.append('<section><h2>Per todo</h2><p class="lede">Siste 30 etter aktivitet. Koordinatorkostnaden fordeles ikke per todo.</p>'
             '<div class="scroll"><table><thead><tr><th>Todo</th><th>Sist aktiv</th><th class="num">Plan</th><th class="num">Impl.</th>'
             '<th class="num">Review</th><th class="num">Scout</th><th class="num">Totalt</th><th class="num">Gate F</th><th class="num">Review-runder</th><th>Utfall</th></tr></thead><tbody>')
    for nr, p in todo_rows:
        info = rl.get(nr, {})
        oc = info.get('outcome', '')
        pill = f'<span class="pill {"ok" if oc == "merged" else "wip"}">{esc(oc or "pågår")}</span>'
        gf = info.get('gate_f')
        h.append(f'<tr><td class="mono">{esc(nr)}</td><td class="muted">{esc(local(p["last"]).strftime("%d.%m %H:%M"))}</td>'
                 f'<td class="num">{money(p["plan"])}</td><td class="num">{money(p["impl"])}</td><td class="num">{money(p["rev"])}</td>'
                 f'<td class="num">{p["scout"]}</td><td class="num strong">{money(p["usd"])}</td>'
                 f'<td class="num">{"–" if gf is None else gf}</td><td class="num">{esc(info.get("review_rounds", "–"))}</td><td>{pill}</td></tr>')
    h.append('</tbody></table></div></section>')
    h.append('<footer class="muted">Generert av <code>python3 tasks/measure-cost.py &lt;since&gt; --html &lt;sti&gt;</code>. '
             'Usage dedupliseres per message.id. Agentkost føres på startdagen.</footer></main>')
    open(path, 'w', encoding='utf-8').write('\n'.join(h) + '\n')


def effort_section(rows, coord, rl, cutover):
    """Koordinator-effort: medium → high (13.09) og high før/etter kostnadsgrepene (15.09).

    Periodene avgrenses av når effort-verdien i transkriptet skifter, ikke av en hardkodet dato.
    Todos tilordnes perioden implementeren startet i. Sammenligningen er ikke kontrollert: andre
    endringer (V-blokk-krav, kostnadsgrep) skjedde samtidig, og utvalgene er små.
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

    impl_start = {}
    for r in rows:
        if r['role'] == 'implementer' and r['todo'] != '-':
            impl_start[r['todo']] = min(impl_start.get(r['todo'], r['t0']), r['t0'])
    agent_usd = defaultdict(float)
    for r in rows:
        agent_usd[r['todo']] += r['usd']

    cols = []
    for name, a, b in periods:
        cs = [c for c in coord if inside(c[0], a, b)]
        hours = len({local(c[0]).strftime('%Y-%m-%d %H') for c in cs})
        todos = [n for n, t in impl_start.items() if inside(t, a, b) and rl.get(n, {}).get('outcome') == 'merged']
        gf = [rl[n]['gate_f'] for n in todos if rl[n].get('gate_f') is not None]
        rr = [int(rl[n]['review_rounds']) for n in todos if str(rl[n].get('review_rounds', '')).isdigit()]
        pr = [int(rl[n]['plan_rounds']) for n in todos if str(rl[n].get('plan_rounds', '')).isdigit()]
        cusd = sum(c[1] for c in cs)
        cols.append({
            'name': name,
            'span': (local(a).strftime('%d.%m %H:%M') if a else 'start') + ' – ' + (local(b).strftime('%d.%m %H:%M') if b else 'nå'),
            'Kall': f'{len(cs):,}',
            'Aktive timer': str(hours),
            'Koordinator $ totalt': money(cusd),
            '$ per kall': money(cusd / len(cs)) if cs else '–',
            'Output per kall (inkl. tenking)': f'{sum(c[5] for c in cs) / len(cs):,.0f}' if cs else '–',
            'Snittkontekst per kall': f'{sum(c[2] for c in cs) / len(cs) / 1000:,.0f}k' if cs else '–',
            'Kall per aktive time': f'{len(cs) / hours:,.0f}' if hours else '–',
            'Leverte todos (impl. startet her)': str(len(todos)),
            'Agent-$ per levert todo': money(sum(agent_usd[n] for n in todos) / len(todos)) if todos else '–',
            'Gate F-returer per todo': f'{sum(gf) / len(gf):.2f}' if gf else '–',
            'Plan-runder per todo': f'{sum(pr) / len(pr):.1f}' if pr else '–',
            'Kode-review-runder per todo': f'{sum(rr) / len(rr):.1f}' if rr else '–',
        })
    keys = [k for k in cols[0] if k not in ('name', 'span')]
    h = ['<section><h2>Koordinator-effort: medium mot high</h2>',
         f'<p class="lede">Effort ble satt fra medium til high {esc(local(switch).strftime("%d.%m kl. %H:%M"))} (fra transkriptet). '
         'Periodene nedenfor er ikke kontrollerte forsøk: V-blokk-kravet og kostnadsgrepene kom i samme tidsrom, og utvalgene er små. '
         'Tolk kvalitetsradene (Gate F og runder) som retning, ikke som bevis.</p>',
         '<div class="scroll"><table><thead><tr><th>Mål</th>']
    for c in cols:
        h.append(f'<th class="num">{esc(c["name"])}<br><span class="muted mono" style="font-weight:400">{esc(c["span"])}</span></th>')
    h.append('</tr></thead><tbody>')
    for k in keys:
        h.append(f'<tr><td>{esc(k)}</td>' + ''.join(f'<td class="num">{c[k]}</td>' for c in cols) + '</tr>')
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
