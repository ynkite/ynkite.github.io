# -*- coding: utf-8 -*-
"""저장소에 올릴 파일 목록을 만든다.

HTML·JS·SVG가 실제로 참조하는 자산만 고른다. 원본 캡처 모음과 백업,
참조가 끊긴 파일은 뺀다. `python tools/manifest.py` 로 목록만 확인할 수 있다.
"""
import glob
import io
import os
import re
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ['index.html'] + sorted(glob.glob('projects/*.html'))
SKIP_DIRS = ('프로젝트 사진', '_backup', '_workspace', '__pycache__')
# 어느 HTML도 가리키지 않지만 올려야 하는 것 — 본편 PDF가 이 주소로 링크한다
EXTRA = ('assets/포트폴리오_정상연_산출물.pdf',)
ASSET_EXT = r'png|jpg|jpeg|svg|mp4|pdf|webp|ico'


def _norm(p):
    return os.path.normpath(p).replace('\\', '/')


def referenced():
    """페이지와 그 안의 스크립트가 가리키는 자산 경로를 모은다."""
    out = set()
    for page in PAGES:
        s = io.open(page, encoding='utf-8').read()
        base = os.path.dirname(page)
        # 마크업의 src/href
        for m in re.findall(r'(?:src|href)="((?!https?:|mailto:|tel:|#|data:)[^"]+)"', s):
            out.add(_norm(os.path.join(base, unquote(m.split('#')[0].split('?')[0]))))
        # 스크립트 안에 문자열로 박아 둔 갤러리 사진
        for m in re.findall(r"'((?:\.\./)?assets/[^']+\.(?:%s))'" % ASSET_EXT, s):
            out.add(_norm(unquote(m.replace('../', ''))))
    for f in glob.glob('assets/*.js') + glob.glob('assets/*.svg'):
        s = io.open(f, encoding='utf-8', errors='replace').read()
        for m in re.findall(r"""['"(]((?:\.\./)?assets/[^'")]+\.(?:%s))""" % ASSET_EXT, s):
            out.add(_norm(unquote(m.replace('../', ''))))
    return out


def present():
    out = set()
    for top in ('assets', 'projects', 'tools'):
        for r, ds, fs in os.walk(top):
            ds[:] = [d for d in ds if d not in SKIP_DIRS]
            if any(k in r for k in SKIP_DIRS):
                continue
            for x in fs:
                out.add(_norm(os.path.join(r, x)))
    out.add('index.html')
    return out


def plan():
    """(올릴 파일, 빼는 파일) 을 돌려준다."""
    ref = referenced() | set(EXTRA)
    have = present()
    keep, drop = set(['index.html']), set()
    for p in have:
        if p == 'index.html':
            continue
        if p.startswith('projects/'):
            keep.add(p)
        elif p.startswith('tools/'):
            keep.add(p) if p.endswith('.py') else drop.add(p)
        elif p in ref:
            keep.add(p)
        else:
            drop.add(p)
    return sorted(keep), sorted(drop), sorted(r for r in ref if not os.path.exists(r))


if __name__ == '__main__':
    os.chdir(ROOT)
    keep, drop, missing = plan()
    total = sum(os.path.getsize(p) for p in keep)
    print('올릴 파일 %d개  %.1fMB' % (len(keep), total / 1048576.0))
    for p in keep:
        if os.path.getsize(p) > 512 * 1024:
            print('   큰 파일  %-44s %6.1fMB' % (p, os.path.getsize(p) / 1048576.0))
    print('\n빼는 파일 %d개  %.1fMB' % (len(drop), sum(os.path.getsize(p) for p in drop) / 1048576.0))
    for p in drop:
        print('   %-46s %7.2fMB' % (p, os.path.getsize(p) / 1048576.0))
    print('\n참조는 있는데 파일이 없는 것:', missing or '없음')
