# -*- coding: utf-8 -*-
"""Minimal dependency-free PDF text extractor (Type0/Identity-H + ToUnicode)."""
import re, sys, zlib, os

class PDF:
    def __init__(self, path):
        self.data = open(path, 'rb').read()
        self.objs = {}
        self.streams = {}
        self._scan()

    def _scan(self):
        for m in re.finditer(rb'(?<![0-9])(\d+)\s+(\d+)\s+obj\b', self.data):
            num = int(m.group(1))
            start = m.end()
            end = self.data.find(b'endobj', start)
            if end < 0:
                end = len(self.data)
            self.objs[num] = self.data[start:end]
        # build stream index
        for num, body in self.objs.items():
            si = body.find(b'stream')
            if si >= 0:
                self.streams[num] = self._stream_bytes(body, si)

    def _stream_bytes(self, body, si):
        s = si + 6
        if body[s:s+2] == b'\r\n':
            s += 2
        elif body[s:s+1] in (b'\n', b'\r'):
            s += 1
        e = body.find(b'endstream', s)
        raw = body[s:e] if e >= 0 else body[s:]
        if b'/FlateDecode' in body[:si]:
            try:
                return zlib.decompress(raw)
            except Exception:
                try:
                    return zlib.decompressobj().decompress(raw)
                except Exception:
                    return b''
        return raw

    def get(self, num):
        return self.objs.get(num, b'')

    def resolve_ref(self, token):
        m = re.match(rb'\s*(\d+)\s+\d+\s+R', token)
        return int(m.group(1)) if m else None


def parse_cmap(txt):
    """Return dict code->unicode string from a ToUnicode CMap stream."""
    cmap = {}
    for m in re.finditer(rb'beginbfchar(.*?)endbfchar', txt, re.S):
        for mm in re.finditer(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', m.group(1)):
            src = int(mm.group(1), 16)
            cmap[src] = hex_to_utf16be(mm.group(2))
    for m in re.finditer(rb'beginbfrange(.*?)endbfrange', txt, re.S):
        body = m.group(1)
        for mm in re.finditer(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', body):
            lo, hi = int(mm.group(1), 16), int(mm.group(2), 16)
            base = mm.group(3)
            n = len(base) // 4 or 1
            try:
                start = int(base, 16)
            except ValueError:
                continue
            for i in range(min(hi - lo + 1, 65536)):
                cmap[lo + i] = int_to_utf16be(start + i)
        for mm in re.finditer(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]', body, re.S):
            lo = int(mm.group(1), 16)
            items = re.findall(rb'<([0-9A-Fa-f]+)>', mm.group(3))
            for i, it in enumerate(items):
                cmap[lo + i] = hex_to_utf16be(it)
    return cmap


def int_to_utf16be(v):
    if v > 0xFFFF:
        v -= 0x10000
        return chr(0xD800 + (v >> 10)) + chr(0xDC00 + (v & 0x3FF))
    return chr(v)


def hex_to_utf16be(h):
    h = h.decode() if isinstance(h, bytes) else h
    if len(h) % 4:
        h = h.zfill(len(h) + (4 - len(h) % 4))
    out = []
    for i in range(0, len(h), 4):
        out.append(int_to_utf16be(int(h[i:i+4], 16)))
    return ''.join(out)


def font_maps(pdf, res_body):
    """Map font resource name (e.g. /F1) -> (cmap dict, two_byte bool)."""
    fonts = {}
    m = re.search(rb'/Font\s*<<(.*?)>>', res_body, re.S)
    fontdict_body = m.group(1) if m else None
    fmap = {}
    if fontdict_body:
        for mm in re.finditer(rb'/([A-Za-z0-9_.\-]+)\s+(\d+)\s+\d+\s+R', fontdict_body):
            fmap[mm.group(1).decode()] = int(mm.group(2))
    else:
        m2 = re.search(rb'/Font\s+(\d+)\s+\d+\s+R', res_body)
        if m2:
            fb = pdf.get(int(m2.group(1)))
            for mm in re.finditer(rb'/([A-Za-z0-9_.\-]+)\s+(\d+)\s+\d+\s+R', fb):
                fmap[mm.group(1).decode()] = int(mm.group(2))
    for name, num in fmap.items():
        fb = pdf.get(num)
        two = b'/Type0' in fb
        cmap = {}
        tu = re.search(rb'/ToUnicode\s+(\d+)\s+\d+\s+R', fb)
        if tu:
            s = pdf.streams.get(int(tu.group(1)), b'')
            cmap = parse_cmap(s)
        fonts['/' + name] = (cmap, two)
    return fonts


def unescape_pdf_string(raw):
    out = bytearray()
    i = 0
    while i < len(raw):
        c = raw[i:i+1]
        if c == b'\\':
            n = raw[i+1:i+2]
            if n in (b'n',): out += b'\n'
            elif n == b'r': out += b'\r'
            elif n == b't': out += b'\t'
            elif n in (b'(', b')', b'\\'): out += n
            elif n.isdigit():
                m = re.match(rb'[0-7]{1,3}', raw[i+1:i+4])
                out.append(int(m.group(0), 8) & 0xFF)
                i += len(m.group(0)) - 1
            i += 2
        else:
            out += c
            i += 1
    return bytes(out)


def decode_with_cmap(raw, cmap, two_byte):
    if cmap:
        chars = []
        if two_byte:
            for i in range(0, len(raw) - 1, 2):
                code = (raw[i] << 8) | raw[i+1]
                chars.append(cmap.get(code, ''))
        else:
            for b in raw:
                chars.append(cmap.get(b, chr(b) if 32 <= b < 127 else ''))
        return ''.join(chars)
    return raw.decode('latin-1', 'replace')


TOKEN_RE = re.compile(rb'/([A-Za-z0-9_.\-]+)\s+[\d.]+\s+Tf|\[(.*?)\]\s*TJ|\((?:\\.|[^\\()])*\)\s*Tj|<([0-9A-Fa-f\s]+)>\s*Tj|([\-\d.]+)\s+([\-\d.]+)\s+Td|([\-\d.]+)\s+([\-\d.]+)\s+TD|T\*|([\-\d.]+\s+){6}Tm|ET', re.S)


def page_text(pdf, page_body):
    res = b''
    m = re.search(rb'/Resources\s+(\d+)\s+\d+\s+R', page_body)
    if m:
        res = pdf.get(int(m.group(1)))
    else:
        m = re.search(rb'/Resources\s*<<', page_body)
        if m:
            depth = 0
            i = m.start() + len(b'/Resources')
            start = i
            for j in range(i, len(page_body)):
                ch = page_body[j:j+1]
                if ch == b'<': depth += 1
                elif ch == b'>':
                    depth -= 1
                    if depth == 0:
                        res = page_body[start:j+1]
                        break
    fonts = font_maps(pdf, res)

    # collect content
    content = b''
    cm = re.search(rb'/Contents\s+(\d+)\s+\d+\s+R', page_body)
    if cm:
        content = pdf.streams.get(int(cm.group(1)), b'')
    else:
        cm = re.search(rb'/Contents\s*\[(.*?)\]', page_body, re.S)
        if cm:
            for ref in re.finditer(rb'(\d+)\s+\d+\s+R', cm.group(1)):
                content += pdf.streams.get(int(ref.group(1)), b'') + b'\n'

    cur_font = None
    out = []
    last_y = None
    cur_x = cur_y = 0.0
    pending_break = False

    def emit(text):
        nonlocal last_y, pending_break
        if not text:
            return
        if pending_break or last_y is None or abs(cur_y - last_y) > 0.5:
            if out and not out[-1].endswith('\n'):
                out.append('\n')
            pending_break = False
        last_y = cur_y
        out.append(text)

    for m in TOKEN_RE.finditer(content):
        g = m.group(0)
        if m.group(1):
            cur_font = '/' + m.group(1).decode()
        elif m.group(2) is not None:
            s = m.group(2)
            piece = []
            for part in re.finditer(rb'\((?:\\.|[^\\()])*\)|<([0-9A-Fa-f\s]+)>|([\-\d.]+)', s, re.S):
                if part.group(0).startswith(b'('):
                    raw = unescape_pdf_string(part.group(0)[1:-1])
                    cmap, two = fonts.get(cur_font, ({}, True))
                    piece.append(decode_with_cmap(raw, cmap, two))
                elif part.group(1):
                    raw = bytes.fromhex(re.sub(r'\s', '', part.group(1).decode()))
                    cmap, two = fonts.get(cur_font, ({}, True))
                    piece.append(decode_with_cmap(raw, cmap, two))
                else:
                    try:
                        if float(part.group(0)) < -180:
                            piece.append(' ')
                    except ValueError:
                        pass
            emit(''.join(piece))
        elif g.endswith(b'Tj'):
            if g.startswith(b'<'):
                raw = bytes.fromhex(re.sub(r'\s', '', m.group(3).decode()))
            else:
                raw = unescape_pdf_string(g[g.find(b'(')+1:g.rfind(b')')])
            cmap, two = fonts.get(cur_font, ({}, True))
            emit(decode_with_cmap(raw, cmap, two))
        elif b'Td' in g or b'TD' in g or g == b'T*' or g.endswith(b'Tm'):
            dx = dy = None
            if b'Td' in g or b'TD' in g:
                nums = re.findall(rb'[\-\d.]+', g)
                if len(nums) >= 2:
                    dx, dy = float(nums[-2]), float(nums[-1])
                if dy is not None:
                    cur_x += dx
                    cur_y += dy
            elif g.endswith(b'Tm'):
                nums = re.findall(rb'[\-\d.]+', g)
                if len(nums) >= 6:
                    cur_x, cur_y = float(nums[4]), float(nums[5])
            else:  # T*
                pending_break = True
        elif g == b'ET':
            pending_break = False
    txt = ''.join(out)
    txt = re.sub(r'[ \t]+\n', '\n', txt)
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    return txt


def page_order(pdf):
    """Return page object numbers in reading order via the page tree."""
    root = None
    m = re.search(rb'/Root\s+(\d+)\s+\d+\s+R', pdf.data)
    if m:
        root = int(m.group(1))
    order = []

    def walk(num, depth=0):
        if depth > 8 or num in seen:
            return
        seen.add(num)
        body = pdf.get(num)
        if re.search(rb'/Type\s*/Pages', body):
            kids = re.search(rb'/Kids\s*\[(.*?)\]', body, re.S)
            if kids:
                for ref in re.finditer(rb'(\d+)\s+\d+\s+R', kids.group(1)):
                    walk(int(ref.group(1)), depth + 1)
        elif re.search(rb'/Type\s*/Page[^s]', body):
            order.append(num)

    seen = set()
    if root is not None:
        cat = pdf.get(root)
        pm = re.search(rb'/Pages\s+(\d+)\s+\d+\s+R', cat)
        if pm:
            walk(int(pm.group(1)))
    if not order:
        order = sorted(n for n, b in pdf.objs.items() if re.search(rb'/Type\s*/Page[^s]', b))
    return order


RADICALS = {
    '⻛': '风', '⻓': '长', '⻅': '见', '⻄': '西', '⺠': '民', '⻜': '飞',
    '⻋': '车', '⻝': '食', '⻩': '黄', '⻆': '角', '⻣': '骨', '⻔': '门',
    '⻘': '青', '⻰': '龙', '⻢': '马', '⻥': '鱼', '⻦': '鸟', '⻉': '贝',
}


def normalize(txt):
    import unicodedata
    txt = ''.join(RADICALS.get(ch, ch) for ch in txt)
    txt = unicodedata.normalize('NFKC', txt)
    txt = txt.replace('\u2010', '-').replace('\u2011', '-')
    txt = re.sub(r'[ \t]+', ' ', txt)
    txt = re.sub(r' ?\n ?', '\n', txt)
    return txt


def extract(path):
    pdf = PDF(path)
    pages = page_order(pdf)
    out = []
    for i, p in enumerate(pages, 1):
        body = pdf.get(p)
        out.append('=== PAGE %d ===\n' % i + page_text(pdf, body))
    return normalize('\n'.join(out))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(extract(sys.argv[1]))
