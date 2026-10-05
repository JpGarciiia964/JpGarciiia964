#!/usr/bin/env python3
"""Calendario de contribuciones isométrico 3D con la paleta RST (assets/rst-isocalendar.svg).

Usa GraphQL (contributionCalendar), compatible con tokens fine-grained de solo lectura.
Las contribuciones privadas cuentan solo como números, sin nombres de repos.

Uso: GH_TOKEN=... python scripts/rst_isocalendar.py assets/rst-isocalendar.svg
"""
import datetime as dt, json, math, os, sys, urllib.request

TOKEN = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
QUERY = '''query{viewer{contributionsCollection{restrictedContributionsCount
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}'''

# (tapa, lado izquierdo, lado derecho) por nivel de intensidad
LEVELS = [('#2A2A2A', '#202020', '#1A1A1A'), ('#5C1A22', '#45121A', '#3A0F16'),
          ('#8B0A14', '#6E0810', '#5C060D'), ('#C8102E', '#9E0C24', '#850A1E'), ('#FF3B4E', '#D42A3B', '#B52232')]


def fetch():
    req = urllib.request.Request('https://api.github.com/graphql', data=json.dumps({'query': QUERY}).encode(),
                                 headers={'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if 'errors' in data:
        sys.exit(f'GraphQL: {data["errors"]}')
    return data['data']['viewer']['contributionsCollection']


def streaks(days):
    best = cur = run = 0
    for d in days:
        run = run + 1 if d['contributionCount'] else 0
        best = max(best, run)
    for d in reversed(days):
        if d['contributionCount']:
            cur += 1
        elif d['date'] != dt.date.today().isoformat():
            break
    return cur, best


def build(col):
    cal = col['contributionCalendar']
    weeks = cal['weeks']
    days = [d for w in weeks for d in w['contributionDays']]
    mx = max((d['contributionCount'] for d in days), default=0) or 1
    active = sum(1 for d in days if d['contributionCount'])
    best_day = max(days, key=lambda d: d['contributionCount'])
    cur, best = streaks(days)

    A, C = 12.0, 2.6           # vector de una semana (derecha, abajo)
    B, D = 10.0, 5.0           # vector de un día de la semana (izquierda, abajo)
    k = .86                    # tamaño de la celda (deja una junta entre bloques)
    ox, oy = 480, 120
    cubes = []
    for wi, w in enumerate(weeks):
        for d in w['contributionDays']:
            c, di = d['contributionCount'], d['weekday']
            lvl = 0 if c == 0 else min(4, 1 + int(3 * math.sqrt(c / mx) + .5))
            h = 2 + (60 * math.sqrt(c / mx) if c else 0)
            x = ox + wi * A - di * B
            y = oy + wi * C + di * D - h
            p1 = (x + k * A, y + k * C)
            p2 = (x + k * (A - B), y + k * (C + D))
            p3 = (x - k * B, y + k * D)
            top, left, right = LEVELS[lvl]
            f = lambda pts: 'M' + ' L'.join(f'{px:.1f},{py:.1f}' for px, py in pts) + 'Z'
            cubes.append((wi * C + di * D, f'<path d="{f([(x, y), p1, p2, p3])}" fill="{top}"/>'
                          f'<path d="{f([p3, p2, (p2[0], p2[1] + h), (p3[0], p3[1] + h)])}" fill="{left}"/>'
                          f'<path d="{f([p1, p2, (p2[0], p2[1] + h), (p1[0], p1[1] + h)])}" fill="{right}"/>'))
    cubes.sort(key=lambda c: c[0])
    body = ''.join(c[1] for c in cubes)

    def stat(y, val, lab):
        return (f'<rect x="40" y="{y - 30}" width="4" height="40" fill="#C8102E"/>'
                f'<text x="58" y="{y - 4}" class="v">{val}</text><text x="58" y="{y + 12}" class="l">{lab}</text>')

    bd = dt.date.fromisoformat(best_day['date']).strftime('%d/%m/%Y')
    legend = ''.join(f'<rect x="{1044 + i * 22}" y="40" width="16" height="16" rx="3" fill="{LEVELS[i][0]}"/>' for i in range(5))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="380" viewBox="0 0 1200 380">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#141414"/><stop offset="1" stop-color="#2A2A2A"/></linearGradient>
    <style>
      .k{{font:700 13px 'Inter','Segoe UI',Helvetica,Arial,sans-serif;fill:#E0182F;letter-spacing:3px}}
      .h{{font:800 26px 'Inter','Segoe UI',Helvetica,Arial,sans-serif;fill:#FFFFFF}}
      .v{{font:800 26px 'Inter','Segoe UI',Helvetica,Arial,sans-serif;fill:#FFFFFF}}
      .l{{font:500 13px 'Inter','Segoe UI',Helvetica,Arial,sans-serif;fill:#BDBDBD}}
      .s{{font:400 12px 'Inter','Segoe UI',Helvetica,Arial,sans-serif;fill:#7A7A7A}}
      .city{{animation:rise 1.2s ease-out backwards}}
      @keyframes rise{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:none}}}}
      @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
    </style>
  </defs>
  <rect width="1200" height="380" rx="18" fill="url(#bg)"/>
  <rect x="0" y="0" width="8" height="380" fill="#C8102E"/>
  <text x="40" y="52" class="k">ACTIVIDAD · ÚLTIMOS 12 MESES</text>
  <text x="40" y="88" class="h">El territorio de la manada</text>
  <g class="city">{body}</g>
  {stat(150, cal['totalContributions'], 'contribuciones')}
  {stat(205, col['restrictedContributionsCount'], 'en repos privados')}
  {stat(260, active, 'días activos · mejor racha: ' + str(best))}
  {stat(315, best_day['contributionCount'], f'récord diario · {bd}')}
  <text x="1036" y="53" class="l" text-anchor="end">Menos</text><text x="1158" y="53" class="l">Más</text>
  {legend}
  <text x="40" y="366" class="s">Generado a diario por una GitHub Action · racha actual: {cur} día(s)</text>
</svg>
'''


if __name__ == '__main__':
    if not TOKEN:
        sys.exit('Falta GH_TOKEN')
    open(sys.argv[1], 'w', encoding='utf-8').write(build(fetch()))
    print('->', sys.argv[1])
