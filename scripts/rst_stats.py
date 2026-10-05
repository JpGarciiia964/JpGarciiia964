#!/usr/bin/env python3
"""Genera assets/rst-stats.svg con estadísticas agregadas de todos los repos propios
(públicos y privados). Solo publica totales: nunca nombres de repos privados ni código.

Uso: GH_TOKEN=... python scripts/rst_stats.py assets/rst-stats.svg
"""
import base64, datetime as dt, html, json, os, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = 'https://api.github.com'
TOKEN = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
HERE = os.path.dirname(os.path.abspath(__file__))

LANG_COLORS = ['#C8102E', '#E8455A', '#F08A97', '#9A9A9A', '#6B6B6B', '#4A4A4A']


def get(path, params=None, raw=False):
    url = path if path.startswith('http') else f'{API}{path}'
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {TOKEN}',
                                               'Accept': 'application/vnd.github+json',
                                               'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        return (json.loads(body) if body else None), r.headers


def paged(path, params):
    out, page = [], 1
    while True:
        data, _ = get(path, {**params, 'per_page': 100, 'page': page})
        if not data:
            return out
        out += data
        if len(data) < 100:
            return out
        page += 1


def repo_stats(repo, login, since):
    full = repo['full_name']
    langs, manifests, commits = {}, 0, 0
    try:
        langs, _ = get(f'/repos/{full}/languages')
    except Exception:
        pass
    try:
        tree, _ = get(f'/repos/{full}/git/trees/{repo["default_branch"]}', {'recursive': 1})
        manifests = sum(1 for t in tree.get('tree', []) if t['path'].endswith('__manifest__.py'))
    except Exception:
        pass
    try:
        commits = len(paged(f'/repos/{full}/commits', {'author': login, 'since': since}))
    except Exception:
        pass
    return langs or {}, manifests, commits


def collect():
    me, _ = get('/user')
    login = me['login']
    repos = [r for r in paged('/user/repos', {'affiliation': 'owner'}) if not r['fork'] and not r['archived']]
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)).isoformat()
    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(lambda r: repo_stats(r, login, since), repos))
    langs = {}
    for l, _, _ in results:
        for k, v in l.items():
            langs[k] = langs.get(k, 0) + v
    return {
        'private': sum(r['private'] for r in repos),
        'public': sum(not r['private'] for r in repos),
        'modules': sum(m for _, m, _ in results),
        'commits': sum(c for _, _, c in results),
        'bytes': sum(langs.values()),
        'langs': sorted(langs.items(), key=lambda kv: -kv[1]),
    }


def fmt(n):
    return f'{n:,}'.replace(',', '.')


def svg(s):
    wolf = base64.b64encode(open(os.path.join(HERE, 'wolf.png'), 'rb').read()).decode()
    total = s['bytes'] or 1
    top = s['langs'][:6]
    tiles = [('🔒', fmt(s['private']), 'repos privados'), ('🧩', fmt(s['modules']), 'módulos Odoo versionados'),
             ('⚡', fmt(len(s['langs'])), 'lenguajes en uso'), ('💾', f"{s['bytes'] / 1e6:.1f} MB".replace('.', ','), 'de código fuente')]
    t_svg = ''
    for i, (ico, val, lab) in enumerate(tiles):
        x = 40 + (i % 2) * 250
        y = 120 + (i // 2) * 120
        t_svg += (f'<g class="t" style="animation-delay:{.15 * i:.2f}s">'
                  f'<rect x="{x}" y="{y}" width="230" height="100" rx="14" fill="#1E1E1E" stroke="#3C3C3C"/>'
                  f'<rect x="{x}" y="{y}" width="5" height="100" rx="2" fill="#C8102E"/>'
                  f'<text x="{x + 24}" y="{y + 52}" class="val">{html.escape(val)}</text>'
                  f'<text x="{x + 24}" y="{y + 78}" class="lab">{html.escape(lab)}</text></g>')
    # barra apilada de lenguajes + leyenda
    bar, x = '', 600
    for i, (name, b) in enumerate(top):
        w = max(4, 540 * b / total)
        bar += f'<rect x="{x:.1f}" y="140" width="{w:.1f}" height="14" fill="{LANG_COLORS[i]}"/>'
        x += w
    legend = ''
    for i, (name, b) in enumerate(top):
        lx, ly = 600 + (i % 2) * 270, 190 + (i // 2) * 34
        legend += (f'<circle cx="{lx + 6}" cy="{ly - 5}" r="6" fill="{LANG_COLORS[i]}"/>'
                   f'<text x="{lx + 20}" y="{ly}" class="lg">{html.escape(name)}</text>'
                   f'<text x="{lx + 250}" y="{ly}" class="pct" text-anchor="end">{100 * b / total:.1f} %</text>')
    today = dt.date.today().strftime('%d/%m/%Y')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="380" viewBox="0 0 1200 380">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#141414"/><stop offset="1" stop-color="#2A2A2A"/></linearGradient>
    <clipPath id="barclip"><rect x="600" y="140" width="540" height="14" rx="7"/></clipPath>
    <style>
      .k{{font:700 13px 'Inter','Segoe UI',Helvetica,Arial,sans-serif;fill:#E0182F;letter-spacing:3px}}
      .h{{font:800 26px 'Inter','Segoe UI',Helvetica,Arial,sans-serif;fill:#FFFFFF}}
      .val{{font:800 32px 'Inter','Segoe UI',Helvetica,Arial,sans-serif;fill:#FFFFFF}}
      .lab{{font:500 14px 'Inter','Segoe UI',Helvetica,Arial,sans-serif;fill:#BDBDBD}}
      .ico{{font:28px 'Segoe UI Emoji','Noto Color Emoji',sans-serif}}
      .lg{{font:600 15px 'Inter','Segoe UI',Helvetica,Arial,sans-serif;fill:#E6E6E6}}
      .pct{{font:500 14px 'Fira Code',Consolas,monospace;fill:#9A9A9A}}
      .s{{font:400 12px 'Inter','Segoe UI',Helvetica,Arial,sans-serif;fill:#7A7A7A}}
      .t{{animation:in .6s ease-out backwards}}
      .bar{{animation:grow 1.4s .3s ease-out backwards;transform-origin:600px 147px}}
      @keyframes in{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
      @keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
      @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
    </style>
  </defs>
  <rect width="1200" height="380" rx="18" fill="url(#bg)"/>
  <rect x="0" y="0" width="8" height="380" fill="#C8102E"/>
  <image x="1092" y="22" width="64" height="80" xlink:href="data:image/png;base64,{wolf}"/>
  <text x="40" y="52" class="k">ROOT SYSTEM TECHNOLOGY · CÓDIGO REAL</text>
  <text x="40" y="88" class="h">Lo que construye la manada</text>
  {t_svg}
  <text x="600" y="120" class="k">LENGUAJES · TODOS LOS REPOS</text>
  <g clip-path="url(#barclip)"><rect x="600" y="140" width="540" height="14" fill="#3C3C3C"/><g class="bar">{bar}</g></g>
  {legend}
  <text x="40" y="362" class="s">Totales agregados de {fmt(s['private'] + s['public'])} repos propios (públicos y privados) · sin forks · actualizado el {today}</text>
</svg>
'''


if __name__ == '__main__':
    if not TOKEN:
        sys.exit('Falta GH_TOKEN')
    stats = collect()
    print(json.dumps({k: v for k, v in stats.items() if k != 'langs'}), stats['langs'][:6])
    open(sys.argv[1], 'w', encoding='utf-8').write(svg(stats))
    print('->', sys.argv[1])
