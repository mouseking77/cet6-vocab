# -*- coding: utf-8 -*-
"""Extract the three word-list PDFs to plain text under src/texts/.

Put the PDFs in ./pdfs/ (or pass a directory as the first argument), then run:
    python src/extract_texts.py

The PDFs themselves are not part of the repository - only the extracted text is.
"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(HERE, 'texts')

sys.path.insert(0, HERE)
from pdftext import extract

FILES = {
    's600': '六级考前冲刺600词（博主：梁伟考研英语）(1).pdf',
    'syn': '梁伟·六级高频同义替换（26年新版）.pdf',
    'tr': '梁伟四六级翻译重点词汇.pdf',
}

KEYWORDS = {'s600': ['600'], 'syn': ['同义替换'], 'tr': ['翻译重点词汇']}


def find_pdf(directory, key):
    """Prefer the exact file name, fall back to a keyword match for renamed PDFs."""
    path = os.path.join(directory, FILES[key])
    if os.path.exists(path):
        return path
    for name in sorted(os.listdir(directory)):
        if not name.lower().endswith('.pdf'):
            continue
        if all(w in name for w in KEYWORDS[key]):
            return os.path.join(directory, name)
    return None


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    src_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'pdfs')
    if not os.path.isdir(src_dir):
        print('找不到 PDF 目录：%s' % src_dir)
        print('请把 3 份 PDF 放进 %s 后重试。' % os.path.join(ROOT, 'pdfs'))
        sys.exit(1)
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    for key, name in FILES.items():
        path = find_pdf(src_dir, key)
        if not path:
            print('缺少文件：%s（跳过）' % name)
            continue
        txt = extract(path)
        out = os.path.join(OUT_DIR, key + '.txt')
        io.open(out, 'w', encoding='utf-8').write(txt)
        print('%-5s %6d chars -> %s' % (key, len(txt), out))
