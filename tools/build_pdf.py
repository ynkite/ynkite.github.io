# -*- coding: utf-8 -*-
"""사이트를 그대로 옮긴 제출용 포트폴리오 PDF를 만든다.

사이트는 눌러야 열리는 것이 많다. 라이트박스 사진도, 접힌 자격증·수상도,
칩을 눌러야 나오는 스킬 설명도 DOM에 없거나 숨어 있어서 그냥 인쇄하면
빈 종이가 나온다. 그래서 인쇄 전용 문서를 따로 짜서 전부 펼쳐 놓는다.

디자인은 사이트 CSS를 그대로 쓴다. 상세페이지 CSS는 메인과 34개
셀렉터가 겹치므로 .det 아래로 가둔 뒤 합친다.

A4 가로(297×210mm)의 인쇄 레이아웃 폭은 1123px이다. 이 사이트는 860px
아래로 내려가야 열이 접히니 레이아웃 구조가 데스크톱과 같고, 글자만
상대적으로 커져 종이에서 읽기 좋다.

사용 — python tools/build_pdf.py
산출 — assets/포트폴리오_정상연.pdf, assets/포트폴리오_정상연_산출물.pdf
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets')
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

MAIN_PDF = '포트폴리오_정상연.pdf'
DOCS_PDF = '포트폴리오_정상연_산출물.pdf'
SITE = 'https://ynkite.github.io/portfolio/'
DOCS_URL = 'https://ynkite.github.io/portfolio/assets/%ED%8F%AC%ED%8A%B8%ED%8F%B4%EB%A6%AC%EC%98%A4_%EC%A0%95%EC%83%81%EC%97%B0_%EC%82%B0%EC%B6%9C%EB%AC%BC.pdf'

DETAILS = [
    ('projects/cogi.html',       'COGI',       '#1c4f8c'),
    ('projects/triplinker.html', 'TripLinker', '#a85c28'),
    ('projects/omong.html',      '오몽',        '#E07B1E'),
]

# 메인 프로젝트는 쓰는 순서대로, 서브는 대표 화면 한 장씩
SHOTS = {
    'work': ('COGI — 실제 화면', 'pfwide', [
        ('cogi-01-dashboard.png',     '대시보드 — 학습일 · 크레딧 · 약점 집계'),
        ('cogi-04-review.png',        'AI 리뷰 결과'),
        ('cogi-06-learning-card.png', '학습 카드 — 개념 · 예제 · 퀴즈'),
        ('cogi-07-skill-recommend.png', 'AI 스킬 추천'),
        ('cogi-08-weekly-report.png', '주간 리포트 메일'),
        ('cogi-02-retention.png',     '리텐션 — streak와 코기 상태'),
    ]),
    'triplinker': ('TripLinker — 실제 화면', 'pfwide', [
        ('tl-02-plan-basic.png', '플랜 만들기 — 기본 정보'),
        ('tl-03-plan-taste.png', '플랜 만들기 — 취향 설정'),
        ('tl-05-day1.jpg',       '1일차 경로 — 지도와 순서'),
        ('tl-07-reorder.jpg',    '장소 순서 교체 결과'),
        ('tl-09-chat.png',       'AI 챗봇 — 플랜 수정 요청'),
        ('tl-11-ledger.png',     '가계부 — 지출 내역'),
    ]),
    'omong': ('오몽 — 실제 화면', 'pfphone', [
        ('omong-01-home.png',   '홈 — 말하기 · 사진 · 제보'),
        ('omong-04-narrow.png', 'AI 대화로 메뉴 좁히기'),
        ('omong-06-guide2.png', '화면 안내 — 메뉴 위치 짚어주기'),
        ('omong-08-staff.png',  '직원에게 보여주기'),
        ('omong-10-vision.png', '사진에서 브랜드 인식'),
        ('omong-02-bigtext.png', '같은 화면, 큰글씨 모드'),
    ]),
}

TILE_SHOTS = {
    'stagepass':  ('sp-01-home.jpg',     '메인 — 추천 공연'),
    'windycamp':  ('wc-03-detail.jpg',   '상품 상세'),
    'deviceshop': ('ds-02-sales.jpg',    '기간별 매출입 현황'),
    'petvillage': ('pv-01-ai-name.jpg',  'AI 이름 추천'),
    'triplan':    ('triplan-01-main.png', '메인 화면'),
    'festa':      ('festa-01-paper.png', '분석 산출물'),
}


IMGDIR = '_pdfimg'
IMGMAX = 1100   # PDF에서 한 장이 차지하는 폭의 두 배쯤. 확대해도 읽히고 파일은 가볍다


def shrink_images(html):
    """PDF에 박히는 사진을 표시 크기에 맞게 줄인다. 원본 그대로면 14MB가 넘는다."""
    out = os.path.join(ROOT, IMGDIR)
    if os.path.isdir(out):
        shutil.rmtree(out)
    used = sorted(set(re.findall(r'src="(assets/[^"]+\.(?:png|jpg|jpeg))"', html)))
    for rel in used:
        dst = os.path.join(out, rel.replace('assets/', ''))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im = Image.open(os.path.join(ROOT, rel))
        # ERD·도식은 확대해서 읽는 그림이라 원본 해상도로 둔다
        keep = any(k in rel for k in ('-erd', '-arch', '-flow'))
        if im.width > IMGMAX and not keep:
            im = im.resize((IMGMAX, int(round(im.height * IMGMAX / float(im.width)))), Image.LANCZOS)
        if im.mode in ('RGBA', 'LA', 'P'):
            im.save(dst, optimize=True)          # 투명도가 있으면 PNG 그대로
        else:
            dst = os.path.splitext(dst)[0] + '.jpg'
            im.convert('RGB').save(dst, quality=84, optimize=True, progressive=True)
        html = html.replace('src="%s"' % rel,
                            'src="%s/%s"' % (IMGDIR, os.path.relpath(dst, out).replace(os.sep, '/')))
    tot = sum(os.path.getsize(os.path.join(r, f))
              for r, _, fs in os.walk(out) for f in fs)
    print('  사진 %d장 → %.1fMB' % (len(used), tot / 1048576.0))
    return html


# ────────────────────────────── 읽기 ──────────────────────────────

def read(p):
    return io.open(os.path.join(ROOT, p), encoding='utf-8').read()


def style_of(html):
    return re.search(r'<style>(.*?)</style>', html, re.S).group(1)


def between(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


# ─────────────────────────── CSS 가두기 ───────────────────────────

def _blocks(css):
    """CSS를 (셀렉터, 본문) 목록으로 자른다."""
    out, sel, i = [], '', 0
    while i < len(css):
        c = css[i]
        if c == '{':
            depth, j = 1, i + 1
            while j < len(css) and depth:
                if css[j] == '{':
                    depth += 1
                elif css[j] == '}':
                    depth -= 1
                j += 1
            out.append((sel.strip(), css[i + 1:j - 1]))
            sel, i = '', j
        elif c == '}':
            i += 1
        else:
            sel += c
            i += 1
    return out


def scope(css, pre):
    """모든 셀렉터를 pre 아래로 가둔다. 겹치는 이름이 메인을 덮지 않게."""
    out = []
    for sel, body in _blocks(css):
        if sel.startswith('@'):
            if sel.startswith(('@media', '@supports')):
                out.append('%s{%s}' % (sel, scope(body, pre)))
            else:
                out.append('%s{%s}' % (sel, body))
            continue
        news = []
        for s in (x.strip() for x in sel.split(',')):
            if not s:
                continue
            if s in ('html', 'body', ':root'):
                news.append(pre)
            elif s == '*':
                news.append(pre + ',' + pre + ' *')
            else:
                for head in ('html ', 'body ', '.js ', 'html.js '):
                    if s.startswith(head):
                        s = s[len(head):]
                        break
                news.append(pre + ' ' + s)
        out.append('%s{%s}' % (','.join(news), body))
    return ''.join(out)


# ─────────────────────────── 본문 손질 ───────────────────────────

def drop_tag(html, opener, tag='div'):
    """opener로 시작하는 요소를 통째로 지운다."""
    while opener in html:
        i = html.index(opener)
        depth, j = 0, i
        for m in re.finditer(r'<%s\b|</%s>' % (tag, tag), html[i:]):
            if m.group(0).startswith('</'):
                depth -= 1
                if depth == 0:
                    j = i + m.end()
                    break
            else:
                depth += 1
        html = html[:i] + html[j:]
    return html


def figures(shots, kind):
    cells = ''.join(
        '<figure class="pf"><img src="assets/image/%s" alt="%s"><figcaption>%s</figcaption></figure>'
        % (f, c, c) for f, c in shots)
    return '<div class="pfgrid %s">%s</div>' % (kind, cells)


def build_main():
    idx = read('index.html')
    body = between(idx, '<section class="about', '<div class="imglb"')

    body = body.replace(' snap"', '"').replace(' snap ', ' ')
    body = re.sub(r'<details class="fold"', '<details open class="fold"', body)
    # 표지가 같은 내용을 이미 담고 있다
    body = drop_tag(body, '<div class="hero">')

    # 라이트박스 버튼은 눌리지 않는다. 그 자리에 사진을 편다
    for sec, (title, kind, shots) in SHOTS.items():
        blk = ('<div class="wrap"><div class="pfblk"><h4 class="pfh">%s</h4>%s</div></div>'
               % (title, figures(shots, kind)))
        i = body.index('id="%s"' % sec)
        j = body.index('</section>', i)
        body = body[:j] + blk + body[j:]
    for key, (f, cap) in TILE_SHOTS.items():
        mark = 'data-lb="%s"' % key
        i = body.index(mark)
        k = body.rindex('<div class="tbtns">', 0, i)
        fig = ('<figure class="pf tilepf"><img src="assets/image/%s" alt="%s">'
               '<figcaption>%s</figcaption></figure>' % (f, cap, cap))
        body = body[:k] + fig + body[k:]
    # 눌리지 않는 버튼은 뺀다. 상세는 이 문서 뒤에 그대로 붙어 있다
    body = re.sub(r'<button class="(?:pbtn|tbtn)"[^>]*data-lb="[^"]*"[^>]*>.*?</button>', '', body, flags=re.S)
    body = re.sub(r'<a class="pbtn dark" href="\./projects/[^"]*">.*?</a>', '', body, flags=re.S)
    # 제목에 걸린 상세 링크는 로컬 경로다. PDF에서는 배포된 주소로 바꾼다
    body = body.replace('href="./projects/', 'href="' + SITE + 'projects/')

    return body


def build_detail(path, brand):
    h = read(path)
    body = between(h, '<header class="phead">', '<script>')
    body = drop_tag(body, '<div class="videosec"')
    body = drop_tag(body, '<div class="imglb"')
    # 문서 버튼은 눌리지 않으니 별첨을 가리킨다
    body = re.sub(
        r'<div class="docbtns">.*?</div>',
        '<p class="dochint">산출물 문서는 별첨 <a href="%s">「포트폴리오_정상연_산출물.pdf」</a>에 실었습니다.</p>' % DOCS_URL,
        body, flags=re.S)
    body = body.replace('../assets/', 'assets/')
    return '<div class="det" style="--brand:%s">%s</div>' % (brand, body)


# ─────────────────────────── 인쇄 CSS ───────────────────────────

PRINT_CSS = """
@page { size: 297mm 210mm; margin: 0 }
html, body { background: #fff }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact }

/* 화면에서만 쓰는 장치들을 꺼 둔다 */
.pdfdoc .rv, .pdfdoc .det .rv { opacity: 1 !important; transform: none !important; animation: none !important }
.pdfdoc .skpanel { display: block !important }
.pdfdoc .skp { visibility: visible !important; opacity: 1 !important; display: block !important;
  grid-area: auto !important; border-top: 1px solid var(--line); padding: 10px 0 }
.pdfdoc .sk { pointer-events: none }
.pdfdoc .fold > summary { list-style: none; cursor: default }
.pdfdoc .fold .more { display: none }
.pdfdoc section { min-height: 0 !important; padding: 26px 0 }
.pdfdoc .feat { --mockh: 380px }
.pdfdoc .foot { display: none }

/* 쪽 나눔 */
.pdfdoc .brk { break-before: page }
.pdfdoc .card, .pdfdoc .drow, .pdfdoc .tile, .pdfdoc .awrow,
.pdfdoc .skp, .pdfdoc .pf, .pdfdoc .abcell, .pdfdoc .fitem { break-inside: avoid }
.pdfdoc h2, .pdfdoc h3, .pdfdoc .shead, .pdfdoc .step { break-after: avoid }

/* 더 많은 작업 — 종이에서는 2열이라야 사진이 읽힌다 */
.pdfdoc .tiles { grid-template-columns: 1fr 1fr !important }

/* 실제 화면 */
.pdfdoc .pfblk { margin-top: 26px }
.pdfdoc .pfh { font-size: 15px; font-weight: 650; letter-spacing: -.01em; margin-bottom: 12px; color: var(--sub) }
.pdfdoc .pfgrid { display: grid; gap: 14px; align-items: start }
.pdfdoc .pfgrid.pfwide { grid-template-columns: 1fr 1fr }
.pdfdoc .pfgrid.pfphone { grid-template-columns: repeat(3, 1fr) }
.pdfdoc .pf { margin: 0; border: 1px solid var(--line); border-radius: 12px; overflow: hidden; background: #fff }
.pdfdoc .pf img { width: 100%; display: block }
.pdfdoc .pfgrid.pfphone .pf img { background: #f6f6f8 }
.pdfdoc .pf figcaption { padding: 8px 11px; font-size: 12px; color: var(--sub);
  border-top: 1px solid var(--line); letter-spacing: .01em }
.pdfdoc .tilepf { margin: 14px 0 0 }
/* 타일 사진은 전체 페이지 캡처라 그대로 두면 카드 높이를 밀어 올린다 */
.pdfdoc .tilepf img { aspect-ratio: 16 / 10; object-fit: cover; object-position: top center }
.pdfdoc .dochint { font-size: 13px; color: var(--muted); margin-top: 14px }
.pdfdoc .dochint a, .pdfdoc .toc .note a { color: var(--blue); text-decoration: underline;
  text-underline-offset: 3px }

/* 표지 · 목차 */
.pdfdoc .cover { height: 793px; display: flex; flex-direction: column; justify-content: center;
  padding: 0 96px; break-after: page }
.pdfdoc .cover .kick { font-size: 15px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted) }
.pdfdoc .cover h1 { font-size: 92px; line-height: .95; letter-spacing: -.055em; margin: 14px 0 10px }
.pdfdoc .cover .sub { font-size: 27px; font-weight: 600; color: var(--sub); letter-spacing: -.02em }
.pdfdoc .cover .lead { margin-top: 28px; font-size: 16px; line-height: 1.75; color: var(--sub); max-width: 720px }
.pdfdoc .cover .site { display: inline-block; margin-top: 34px; font-size: 17px; font-weight: 650;
  color: var(--blue); border-bottom: 2px solid var(--blue); padding-bottom: 3px }
.pdfdoc .cover .works { margin-top: 34px; font-size: 14.5px; color: var(--sub); line-height: 1.8;
  max-width: 760px; padding-top: 20px; border-top: 1px solid var(--line) }
.pdfdoc .cover .works b { display: block; font-size: 12px; letter-spacing: .1em; text-transform: uppercase;
  color: var(--muted); font-weight: 700; margin-bottom: 6px }
.pdfdoc .cover .meta { margin-top: auto; padding-top: 40px; font-size: 14px; color: var(--muted);
  display: flex; gap: 22px; flex-wrap: wrap }
.pdfdoc .toc { padding: 78px 96px 0; break-after: page }
.pdfdoc .toc h2 { font-size: 34px; letter-spacing: -.035em; margin-bottom: 26px }
.pdfdoc .toc ol { list-style: none; counter-reset: t }
.pdfdoc .toc li { counter-increment: t; display: flex; align-items: baseline; gap: 14px;
  padding: 11px 0; border-bottom: 1px solid var(--line); font-size: 16px }
.pdfdoc .toc li::before { content: counter(t, decimal-leading-zero); font-variant-numeric: tabular-nums;
  font-weight: 700; color: var(--muted); font-size: 13px }
.pdfdoc .toc li b { font-weight: 650 }
.pdfdoc .toc li span { color: var(--muted); font-size: 13.5px; margin-left: auto }
.pdfdoc .toc .note { margin-top: 22px; font-size: 13.5px; color: var(--muted); line-height: 1.7 }
"""

DOCS_CSS = """
@page { size: 297mm 210mm; margin: 0 }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact;
  font-family: var(--sans); color: var(--ink); background: #fff; margin: 0 }
.dwrap { padding: 34px 40px }
.dsec { break-before: page }
.dsec:first-of-type { break-before: auto }
.dhd { display: flex; align-items: baseline; gap: 12px; margin-bottom: 4px }
.dhd h2 { font-size: 22px; letter-spacing: -.025em }
.dhd .pj { font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
  color: #fff; background: var(--brand); border-radius: 980px; padding: 4px 11px }
.dsrc { font-size: 12px; color: var(--muted); margin-bottom: 12px }
.lgd { display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 12px; font-size: 12px }
.lgd span { display: inline-flex; align-items: center; gap: 6px; color: var(--sub); font-weight: 600 }
.lgd i { width: 22px; height: 11px; border-radius: 6px; box-shadow: inset 0 0 0 1px rgba(0,0,0,.06) }
table { border-collapse: collapse; width: 100%; font-size: 11.5px }
th, td { border: 1px solid var(--line); padding: 5px 8px; text-align: left; vertical-align: top;
  white-space: pre-wrap; word-break: keep-all; overflow-wrap: break-word }
th { background: var(--brand); color: #fff; font-weight: 600; white-space: nowrap; letter-spacing: -.01em }
thead { display: table-header-group }
tr { break-inside: avoid }
tbody tr:nth-child(even) { background: #fafafc }
td:first-child { white-space: nowrap; font-weight: 600 }
tr.grp td { background: #eef1f6; font-weight: 700 }
td.bar { padding: 4px 4px; min-width: 46px }
td.bar span { display: block; height: 12px; border-radius: 7px; box-shadow: inset 0 0 0 1px rgba(0,0,0,.06) }
td.st { white-space: nowrap; font-weight: 600 }
"""


def esc(t):
    return (str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def docs_html():
    """산출물 문서 17종을 표로 편다. docviewer의 렌더 규칙을 그대로 옮겼다."""
    base = style_of(read('index.html'))
    root = re.search(r':root\s*\{(.*?)\}', base, re.S).group(1)
    parts = []
    for js, pj, brand in [('docs-cogi.js', 'COGI', '#1c4f8c'),
                          ('docs-tl.js', 'TripLinker', '#a85c28'),
                          ('docs-om.js', '오몽', '#E07B1E')]:
        raw = read('assets/' + js).strip()
        data = json.loads(raw[raw.index('=') + 1:].rstrip().rstrip(';'))
        for key, d in data.items():
            rows = []
            for r in d['rows']:
                if isinstance(r, dict) and 'g' in r:
                    rows.append('<tr class="grp"><td colspan="%d">%s</td></tr>'
                                % (len(d['head']), esc(r['g'])))
                    continue
                cells = r.get('c', r) if isinstance(r, dict) else r
                bars = r.get('b') if isinstance(r, dict) else None
                tds = []
                for i in range(len(d['head'])):
                    v = cells[i] if i < len(cells) else ''
                    st = {'완료': 'done', '진행': 'now', '예정': 'todo'}.get(v)
                    if bars and str(i) in bars:
                        tds.append('<td class="bar"><span style="background:%s"></span></td>' % bars[str(i)])
                    elif st:
                        tds.append('<td class="st %s">%s</td>' % (st, esc(v)))
                    else:
                        tds.append('<td>%s</td>' % esc(v or ''))
                rows.append('<tr>%s</tr>' % ''.join(tds))
            lgd = ''
            if d.get('legend'):
                lgd = '<div class="lgd">%s</div>' % ''.join(
                    '<span><i style="background:%s"></i>%s</span>' % (it['color'], esc(it['who']))
                    for it in d['legend'])
            parts.append(
                '<section class="dsec" style="--brand:%s">'
                '<div class="dhd"><span class="pj">%s</span><h2>%s</h2></div>'
                '<div class="dsrc">%s · 시트 「%s」 · %d행</div>%s'
                '<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></section>'
                % (brand, esc(pj), esc(d['label']), esc(d['file']), esc(d['sheet']),
                   len(d['rows']), lgd,
                   ''.join('<th>%s</th>' % esc(h or '·') for h in d['head']),
                   ''.join(rows)))
    cover = (
        '<section class="dsec" style="--brand:#1c4f8c;break-before:auto">'
        '<div class="dhd"><h2>산출물 문서 — 별첨</h2></div>'
        '<div class="dsrc">정상연 · 포트폴리오 별첨 · 총 17종 1,526행. '
        '본편은 「포트폴리오_정상연.pdf」입니다.</div></section>')
    return ('<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">'
            '<title>정상연 — 포트폴리오 산출물</title>'
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/'
            'dist/web/variable/pretendardvariable-dynamic-subset.min.css">'
            '<style>:root{%s}%s</style></head><body><div class="dwrap">%s%s</div></body></html>'
            % (root, DOCS_CSS, cover, ''.join(parts)))


COVER = """
<section class="cover">
  <div class="kick">Backend Developer</div>
  <h1>정상연</h1>
  <div class="sub">Java · Spring · Spring AI · AWS</div>
  <p class="lead">인덕대학교 컴퓨터소프트웨어학과에 재학 중입니다.
    대우능력개발원 KDT 과정에서 Java·Spring·AWS·시큐어코딩·Spring AI를 다뤘습니다.
    팀 프로젝트 COGI와 TripLinker에서 팀장을 맡아 AWS 배포까지 마쳤습니다.</p>
  <a class="site" href="{site}">{site} ↗</a>
  <div class="works"><b>수록 프로젝트</b>COGI · TripLinker · 오몽 · StagePass · WindyCamp
    · DEVICE SHOP · PetVillage · Triplan · Analyze Festa</div>
  <div class="meta">
    <span>j.sangyeon6@gmail.com</span><span>010-4211-3521</span>
    <span>github.com/ynkite</span><span>my-commit.tistory.com</span>
  </div>
</section>
<section class="toc">
  <h2>목차</h2>
  <ol>
    <li><b>프로필</b><span>이름 · 학력 · 스킬 · 경력 · 연락처</span></li>
    <li><b>스킬</b><span>Backend · AI · DB · Frontend, 칩별 설명 21건</span></li>
    <li><b>자격증 · 수상 · 교육</b><span>자격증 5 · 경진대회 8 · KDT 1024h</span></li>
    <li><b>COGI</b><span>AI 코드 리뷰 학습 플랫폼 — 개요와 실제 화면 6장</span></li>
    <li><b>TripLinker</b><span>AI 여행 플래너 — 개요와 실제 화면 6장</span></li>
    <li><b>오몽</b><span>키오스크 도우미 — 개요와 실제 화면 6장</span></li>
    <li><b>더 많은 작업</b><span>StagePass · WindyCamp · DEVICE SHOP · PetVillage · Triplan · Analyze Festa</span></li>
    <li><b>링크 · 연락처</b></li>
    <li><b>COGI 상세</b><span>분석 · 설계 · 개발 · 배포와 테스트 · 내 역할 · 트러블슈팅</span></li>
    <li><b>TripLinker 상세</b><span>같은 구성</span></li>
    <li><b>오몽 상세</b><span>같은 구성</span></li>
  </ol>
  <p class="note">산출물 문서 17종(요구사항 정의서 · 기능 정의서 · WBS · API 명세서 ·
    테이블 정의서 · 테스트 케이스 · AI 활용 로그, 총 1,526행)은 분량이 커서
    별첨 <a href="{docs}">「포트폴리오_정상연_산출물.pdf」</a>로 나눴습니다.</p>
</section>
"""


def build():
    idx = read('index.html')
    css_main = style_of(idx)
    css_det = scope(style_of(read('projects/cogi.html')), '.det')
    css_det += scope(style_of(read('projects/omong.html')), '.det')

    parts = [COVER.replace('{site}', SITE).replace('{docs}', DOCS_URL), build_main()]
    for path, name, brand in DETAILS:
        parts.append('<div class="brk"></div>')
        parts.append(build_detail(path, brand))

    html = ('<!DOCTYPE html><html lang="ko" class="js"><head><meta charset="UTF-8">'
            '<title>정상연 — 백엔드 개발자 포트폴리오</title>'
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/'
            'dist/web/variable/pretendardvariable-dynamic-subset.min.css">'
            '<style>%s\n%s\n%s</style></head><body class="pdfdoc">%s</body></html>'
            % (css_main, css_det, PRINT_CSS, ''.join(parts)))

    html = shrink_images(html)
    io.open(os.path.join(ROOT, '_pdf.html'), 'w', encoding='utf-8', newline='').write(html)
    io.open(os.path.join(ROOT, '_pdf_docs.html'), 'w', encoding='utf-8', newline='').write(docs_html())
    print('  _pdf.html %dKB / _pdf_docs.html %dKB'
          % (len(html) // 1024, os.path.getsize(os.path.join(ROOT, '_pdf_docs.html')) // 1024))


def render(src, out):
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
                    '--user-data-dir=' + os.path.join(os.environ.get('TEMP', '.'), 'cr_pdf'),
                    '--no-pdf-header-footer', '--virtual-time-budget=60000',
                    '--print-to-pdf=' + out, 'file:///' + src.replace('\\', '/')],
                   check=True, capture_output=True)
    d = open(out, 'rb').read()
    print('  %-34s %5.1fMB  %d쪽' % (os.path.basename(out), len(d) / 1048576.0,
                                     d.count(b'/Type /Page') - d.count(b'/Type /Pages')))


if __name__ == '__main__':
    os.chdir(ROOT)
    build()
    render(os.path.join(ROOT, '_pdf.html'), os.path.join(OUT, MAIN_PDF))
    render(os.path.join(ROOT, '_pdf_docs.html'), os.path.join(OUT, DOCS_PDF))
