# -*- coding: utf-8 -*-
"""Parse the extracted text files into data.json (the app's word database)."""
import io, json, re, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEXT_DIR = os.path.join(HERE, 'texts')
OUT = os.path.join(HERE, 'data.json')

CJK = re.compile(r'[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]')
POS = r'(?:n|v|adj|adv|prep|conj|pron|num|art|int|vt|vi|aux)\.'
POS_RE = re.compile(r'(?<![A-Za-z])(' + POS + r')(?=\s*[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef]|\s*$)')


def clean_zh(s):
    s = re.sub(r'(?<=[\u2e80-\u9fff])\s+(?=[\u2e80-\u9fff])', '', s)
    return s.strip()


def split_pos(s):
    """Split 'adj.短暂的' / 'variety = diversity n.多样性' into (head, pos, zh)."""
    m = POS_RE.search(s)
    if not m:
        return s.strip(), '', ''
    head = s[:m.start()].strip()
    zh = s[m.end():].strip()
    return head, m.group(1), zh


def parse_600(path):
    txt = io.open(path, encoding='utf-8').read()
    lines = [l.strip() for l in txt.splitlines()]
    items = []
    day = None
    day_ranges = {}
    cur = None
    head_re = re.compile(r'^(\d+)\.\s*(.+?)\s*\[([^\]]*)\]\s*(.*)$')
    no_ph_re = re.compile(r'^(\d+)\.\s*(.+?)\s*(?:\[([^\]]*)\])?\s*(' + POS + r')\s*(.*)$')
    for ln in lines:
        if not ln or ln.startswith('==='):
            continue
        m = re.match(r'^第(.+)天\s*\((\d+)\s*-\s*(\d+)\)$', ln)
        if m:
            day = m.group(1)
            day_ranges[day] = (int(m.group(2)), int(m.group(3)))
            continue
        m = re.match(r'^(\d+)\.\s*(.*)$', ln)
        if m and m.group(1).isdigit() and 1 <= int(m.group(1)) <= 600:
            if cur:
                items.append(cur)
            body = m.group(2)
            cur = {'n': int(m.group(1)), 'day': day, 'word': '', 'phon': '', 'pos': '', 'zh': '', 'phr': '', 'phrZh': ''}
            pm = re.match(r'^([A-Za-z][A-Za-z\-\'’\. ]*?)\s*\[([^\]]*)\]\s*(.*)$', body)
            if pm:
                cur['word'] = pm.group(1).strip()
                cur['phon'] = pm.group(2).strip()
                rest = pm.group(3).strip()
            else:
                pm2 = re.match(r'^([A-Za-z][A-Za-z\-\'’\. ]*?)\s*(' + POS + r')\s*(.*)$', body)
                if pm2:
                    cur['word'] = pm2.group(1).strip()
                    rest = pm2.group(2) + ' ' + pm2.group(3)
                else:
                    cur['word'] = body
                    rest = ''
            mm = POS_RE.search(rest)
            if mm:
                cur['pos'] = mm.group(1)
                cur['zh'] = rest[mm.end():].strip()
            else:
                cur['zh'] = rest
            continue
        m = re.match(r'^词组\s*[:：]?\s*(.*)$', ln)
        if m and cur is not None:
            body = m.group(1).strip()
            pm = re.match(r'^(.*?)\s*[（(]\s*(.*?)\s*[）)]\s*$', body)
            if pm:
                cur['phr'] = pm.group(1).strip()
                cur['phrZh'] = pm.group(2).strip()
            else:
                cur['phr'] = body
            continue
    if cur:
        items.append(cur)
    return items, day_ranges


def parse_syn(path):
    txt = io.open(path, encoding='utf-8').read()
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    items = []
    group = ''
    buf = None
    for ln in lines:
        if ln.startswith('==='):
            continue
        m = re.match(r'^[^\w\[]*第(.)组\s*[（(](.*?)[）)]', ln)
        if m:
            if buf:
                items.append(buf)
                buf = None
            group = m.group(2)
            continue
        m = re.match(r'^\[(\d+)\]\s*(.*)$', ln)
        if m:
            if buf:
                items.append(buf)
            buf = {'n': int(m.group(1)), 'group': group, 'raw': m.group(2)}
            continue
        if buf is not None:
            buf['raw'] += ' ' + ln
    if buf:
        items.append(buf)

    out = []
    for b in items:
        raw = re.sub(r'\s+', ' ', b['raw']).strip()
        core, pos, zh = split_pos(raw)
        if not zh:
            # entries without a part-of-speech: the Chinese tail sits after the last variant
            m = re.search(r'([\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f].*)$', core)
            if m:
                zh = m.group(1).strip()
                core = core[:m.start()].strip()
        zh = clean_zh(zh)
        variants = [v.strip() for v in re.split(r'\s*=\s*', core) if v.strip()]
        if not variants:
            continue
        out.append({'n': b['n'], 'group': b['group'], 'variants': variants, 'pos': pos, 'zh': zh})
    return out


def parse_translation(path):
    txt = io.open(path, encoding='utf-8').read()
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    cats = []
    items = []
    cat = ''
    for ln in lines:
        if ln.startswith('==='):
            continue
        if '梁伟' in ln and '词汇' in ln:
            continue
        if CJK.search(ln) and not re.search(r'[A-Za-z]', ln):
            cat = ln
            cats.append(ln)
            continue
        m = re.match(r'^(.*?)\s*([\u3400-\u9fff].*)$', ln)
        if m:
            en, zh = m.group(1).strip(), m.group(2).strip()
            if not en:
                continue
            items.append({'en': en, 'zh': zh, 'cat': cat})
        else:
            # continuation of previous English-only line
            if items and all(ord(c) < 128 for c in ln):
                items[-1]['en'] += ' ' + ln
    return items, cats


def main():
    words_raw, day_ranges = parse_600(os.path.join(TEXT_DIR, 's600.txt'))
    syn_raw = parse_syn(os.path.join(TEXT_DIR, 'syn.txt'))
    tr_raw, cats = parse_translation(os.path.join(TEXT_DIR, 'tr.txt'))

    print('600 words parsed:', len(words_raw))
    bad = [w for w in words_raw if not w['word'] or not w['zh']]
    print('  anomalies:', len(bad))
    for b in bad[:8]:
        print('   ', b)
    print('  with phonetic:', sum(1 for w in words_raw if w['phon']))
    print('  with phrase:', sum(1 for w in words_raw if w['phr']))
    print('  days:', list(day_ranges.items()))

    print('syn parsed:', len(syn_raw))
    sb = [s for s in syn_raw if not s['zh'] or len(s['variants']) < 2]
    print('  anomalies:', len(sb))
    for b in sb[:6]:
        print('   ', b)
    print('  groups:', sorted(set(s['group'] for s in syn_raw)))

    print('translation parsed:', len(tr_raw), 'cats:', cats)
    tb = [t for t in tr_raw if not t['zh']]
    print('  anomalies:', len(tb))
    for b in tb[:5]:
        print('   ', b)

    data = {
        'words': [{'n': w['n'], 'w': w['word'], 'p': w['phon'], 'pos': w['pos'],
                   'zh': w['zh'], 'phr': w['phr'], 'phrZh': w['phrZh'], 'day': w['day']}
                  for w in words_raw],
        'syn': syn_raw,
        'phr': tr_raw,
        'days': [{'d': d, 'from': a, 'to': b} for d, (a, b) in day_ranges.items()],
        'cats': cats,
    }
    out = OUT
    with io.open(out, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
    print('wrote', out, os.path.getsize(out), 'bytes')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
