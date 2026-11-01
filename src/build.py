# -*- coding: utf-8 -*-
"""Inline data.json + build info into the page template -> ../index.html.

Usage:
    python src/build.py

The version string combines src/version.json, the build time and the short git
commit, so a deployed page always tells you which build it is.
"""
import datetime
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(HERE, 'app_template.html')
DATA = os.path.join(HERE, 'data.json')
VERSION = os.path.join(HERE, 'version.json')
OUT = os.path.join(ROOT, 'index.html')


def git_hash():
    try:
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                       cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return 'dev'


def build_string():
    try:
        ver = json.load(io.open(VERSION, encoding='utf-8')).get('version', '0.0.0')
    except Exception:
        ver = '0.0.0'
    stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    return 'v%s · %s · %s' % (ver, stamp, git_hash())


def main():
    if not os.path.exists(DATA):
        print('缺少 %s，请先运行 python src/build_data.py' % DATA)
        return 1
    data = io.open(DATA, encoding='utf-8').read()
    data = data.replace('</', '<\\/')          # keep the JSON safe inside <script>
    html = io.open(TEMPLATE, encoding='utf-8').read()
    if '__DATA__' not in html or '__VERSION__' not in html:
        print('模板里缺少 __DATA__ 或 __VERSION__ 占位符')
        return 1
    info = build_string()
    html = html.replace('__VERSION__', info).replace('__DATA__', data)
    io.open(OUT, 'w', encoding='utf-8').write(html)
    print('wrote %s (%d bytes)  %s' % (OUT, os.path.getsize(OUT), info))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
