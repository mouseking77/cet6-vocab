# -*- coding: utf-8 -*-
"""Inline data.json into the page template -> ../index.html (the file GitHub Pages serves).

Usage:
    python src/build.py
"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(HERE, 'app_template.html')
DATA = os.path.join(HERE, 'data.json')
OUT = os.path.join(ROOT, 'index.html')


def main():
    if not os.path.exists(DATA):
        print('缺少 %s，请先运行 python src/build_data.py' % DATA)
        return 1
    data = io.open(DATA, encoding='utf-8').read()
    data = data.replace('</', '<\\/')          # keep the JSON safe inside <script>
    html = io.open(TEMPLATE, encoding='utf-8').read()
    if '__DATA__' not in html:
        print('模板里没有 __DATA__ 占位符')
        return 1
    html = html.replace('__DATA__', data)
    io.open(OUT, 'w', encoding='utf-8').write(html)
    print('wrote %s (%d bytes)' % (OUT, os.path.getsize(OUT)))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
