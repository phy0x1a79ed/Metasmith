"""Replace the Discussion section of a d2 docx copy with a point-form draft (markdown subset), in blue."""
import re, sys, zipfile, shutil
from xml.sax.saxutils import escape

src, md_path, out = sys.argv[1:4]
md = open(md_path).read()
body = md.split('\n## ', 1)[1]  # drop the file's title and preamble
body = '## ' + body

RPR = '<w:rPr><w:rFonts w:ascii="Arial" w:eastAsia="Arial" w:hAnsi="Arial" w:cs="Arial"/>{b}<w:color w:val="0070C0"/></w:rPr>'

def runs(text):
    out = []
    for i, part in enumerate(re.split(r'\*\*(.+?)\*\*', text)):
        if part:
            out.append(f'<w:r>{RPR.format(b="<w:b/>" if i % 2 else "")}<w:t xml:space="preserve">{escape(part)}</w:t></w:r>')
    return ''.join(out)

def para(text, style=None, indent=0, bullet=''):
    ppr = f'<w:pStyle w:val="{style}"/>' if style else \
        f'<w:spacing w:after="60" w:line="300" w:lineRule="auto"/><w:ind w:left="{indent}" w:hanging="240"/>'
    return f'<w:p><w:pPr>{ppr}</w:pPr>{runs(bullet + text)}</w:p>'

def cell(text, w):
    rpr = '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>{b}<w:color w:val="0070C0"/><w:sz w:val="12"/></w:rPr>'
    rs = ''.join(f'<w:r>{rpr.format(b="<w:b/>" if i % 2 else "")}<w:t xml:space="preserve">{escape(p)}</w:t></w:r>'
                 for i, p in enumerate(re.split(r'\*\*(.+?)\*\*', text)) if p)
    return f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:spacing w:after="0"/></w:pPr>{rs}</w:p></w:tc>'

def table(rows):
    rows = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows if not re.match(r'^\|[-| ]+\|$', r.strip())]
    w = 9000 // len(rows[0])
    border = ''.join(f'<w:{s} w:val="single" w:sz="2" w:color="999999"/>' for s in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'))
    trs = ''.join('<w:tr>' + ''.join(cell(f'**{c}**' if i == 0 and not c.startswith('**') else c, w) for c in r) + '</w:tr>'
                  for i, r in enumerate(rows))
    return f'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders>{border}</w:tblBorders><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>{"".join(f"<w:gridCol w:w=\"{w}\"/>" for _ in rows[0])}</w:tblGrid>{trs}</w:tbl>'

paras, pending = [], []
for line in body.splitlines() + ['']:
    if line.startswith('|'):
        pending.append(line)
        continue
    if pending:
        paras.append(table(pending))
        pending = []
    if not line.strip():
        continue
    if line.startswith('## '):
        paras.append(para(line[3:], style='Heading2'))
    elif m := re.match(r'^( *)- (.*)', line):
        depth = len(m.group(1)) // 2
        paras.append(para(m.group(2), indent=360 + 360 * depth, bullet='• ' if depth == 0 else '◦ '))
    else:
        paras.append(para(line, indent=360))

z = zipfile.ZipFile(src)
x = z.read('word/document.xml').decode()
ps = list(re.finditer(r'<w:p[ >].*?</w:p>', x, re.S))
text = lambda m: ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', m.group(0))).strip()
start = next(m for m in ps if text(m) == 'Discussion')
end = next(m for m in ps if text(m) == 'Conclusion' and m.start() > start.end())
x = x[:start.end()] + ''.join(paras) + x[end.start():]

with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as w:
    for item in z.infolist():
        w.writestr(item, x if item.filename == 'word/document.xml' else z.read(item.filename))
print(f'{len(paras)} paragraphs written to {out}')
