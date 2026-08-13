# -*- coding: utf-8 -*-
import re, collections

P = 'C:/Users/zergu/repos/greenhouse-control/own-article/paper/en/paper_en.tex'
raw = open(P, encoding='utf-8').read()


def strip_comments(t):
    lines = []
    for ln in t.split('\n'):
        out, i = [], 0
        while i < len(ln):
            c = ln[i]
            if c == '\\':
                out.append(ln[i:i + 2]); i += 2; continue
            if c == '%':
                break
            out.append(c); i += 1
        lines.append(''.join(out))
    return '\n'.join(lines)


t = strip_comments(raw)

print('=' * 66)
print('STRUCTURAL CHECK -- paper_en.tex')
print('=' * 66)
print('file: %d lines, %d chars (%d lines of prose+markup after comment strip)'
      % (raw.count('\n') + 1, len(raw), len([l for l in t.split('\n') if l.strip()])))

# --- environments
b = collections.Counter(re.findall(r'\\begin\{([^}]*)\}', t))
e = collections.Counter(re.findall(r'\\end\{([^}]*)\}', t))
print('\n-- environments --')
bad = 0
for k in sorted(set(b) | set(e)):
    flag = '' if b[k] == e[k] else '   <<< UNBALANCED'
    if b[k] != e[k]:
        bad += 1
    print('   %-16s begin=%-3d end=%-3d%s' % (k, b[k], e[k], flag))
print('   TOTAL \\begin = %d, \\end = %d  -> %s'
      % (sum(b.values()), sum(e.values()), 'BALANCED' if bad == 0 else '%d UNBALANCED' % bad))

# --- nesting order
stack, order_ok = [], True
for m in re.finditer(r'\\(begin|end)\{([^}]*)\}', t):
    if m.group(1) == 'begin':
        stack.append(m.group(2))
    else:
        if not stack or stack[-1] != m.group(2):
            order_ok = False
            print('   NESTING ERROR at char %d: \\end{%s} closes %s'
                  % (m.start(), m.group(2), stack[-1] if stack else '<nothing>'))
            break
        stack.pop()
print('   nesting: %s' % ('correct, stack empty' if order_ok and not stack else 'ERROR'))

# --- braces / math
opens = len(re.findall(r'(?<!\\)\{', t))
closes = len(re.findall(r'(?<!\\)\}', t))
dollars = len(re.findall(r'(?<!\\)\$', t))
print('\n-- delimiters --')
print('   braces  {=%d  }=%d  -> %s' % (opens, closes, 'BALANCED' if opens == closes else 'UNBALANCED'))
print('   inline math $ count = %d -> %s' % (dollars, 'even (balanced)' if dollars % 2 == 0 else 'ODD -- UNBALANCED'))

# --- labels / refs
labels = set(re.findall(r'\\label\{([^}]*)\}', t))
refs = collections.Counter(re.findall(r'\\(?:eq)?ref\{([^}]*)\}', t))
dangling = sorted(r for r in refs if r not in labels)
unref = sorted(l for l in labels if l not in refs)
print('\n-- labels and references --')
print('   \\label     : %d' % len(labels))
print('   \\ref/\\eqref: %d calls, %d distinct targets' % (sum(refs.values()), len(refs)))
print('   dangling \\ref (no matching \\label): %d %s' % (len(dangling), dangling if dangling else ''))
print('   labels never referenced           : %d %s' % (len(unref), unref if unref else ''))

# --- floats
figs = len(re.findall(r'\\begin\{figure\}', t))
tabs = len(re.findall(r'\\begin\{table\}', t))
figrefs = sorted(r for r in refs if r.startswith('fig:'))
tabrefs = sorted(r for r in refs if r.startswith('tab:'))
figlab = sorted(l for l in labels if l.startswith('fig:'))
tablab = sorted(l for l in labels if l.startswith('tab:'))
print('\n-- floats --')
print('   figure environments = %d, fig: labels = %d, all cited in text = %s'
      % (figs, len(figlab), set(figlab) == set(figrefs)))
print('   table  environments = %d, tab: labels = %d, all cited in text = %s'
      % (tabs, len(tablab), set(tablab) == set(tabrefs)))
if set(figlab) - set(figrefs):
    print('   UNCITED FIGURES:', sorted(set(figlab) - set(figrefs)))
if set(tablab) - set(tabrefs):
    print('   UNCITED TABLES :', sorted(set(tablab) - set(tabrefs)))

# --- cites / bibitems
cites = collections.Counter()
for m in re.finditer(r'\\cite\{([^}]*)\}', t):
    for k in m.group(1).split(','):
        cites[k.strip()] += 1
bibitems = re.findall(r'\\bibitem\{([^}]*)\}', t)
dupbib = [k for k, n in collections.Counter(bibitems).items() if n > 1]
nocite = sorted(k for k in cites if k not in bibitems)
noref = sorted(k for k in bibitems if k not in cites)
print('\n-- citations and bibliography --')
print('   \\cite calls = %d, distinct keys = %d' % (sum(cites.values()), len(cites)))
print('   \\bibitem    = %d, duplicates = %s' % (len(bibitems), dupbib if dupbib else 'none'))
print('   cited but no bibitem : %d %s' % (len(nocite), nocite if nocite else ''))
print('   bibitem never cited  : %d %s' % (len(noref), noref if noref else ''))
first_ok = bibitems == [k for k in dict.fromkeys(
    [kk.strip() for m in re.finditer(r'\\cite\{([^}]*)\}', t) for kk in m.group(1).split(',')])]
print('   bibitem order == first-citation order: %s' % first_ok)

# --- sections
print('\n-- document structure --')
for m in re.finditer(r'\\(section|subsection)\{([^}]*)\}', t):
    print('   %s%s' % ('   ' if m.group(1) == 'subsection' else '', m.group(2)))

# --- word count (narrative prose only)
body = t
body = re.sub(r'\\begin\{(table|figure|tabular|minipage|thebibliography)\}.*?'
              r'\\end\{\1\}', ' ', body, flags=re.S)
body = re.sub(r'\\begin\{thebibliography\}.*', ' ', body, flags=re.S)
body = re.sub(r'\\begin\{(equation|abstract)\}.*?\\end\{\1\}', ' ', body, flags=re.S)
body = re.sub(r'\\documentclass.*?\\maketitle', ' ', body, flags=re.S)
body = re.sub(r'\$[^$]*\$', ' X ', body)
body = re.sub(r'\\[a-zA-Z]+\*?(\[[^\]]*\])?', ' ', body)
body = re.sub(r'[{}~&\\]', ' ', body)
words = [w for w in re.split(r'\s+', body) if re.search(r'[A-Za-z0-9]', w)]
print('\n-- length --')
print('   narrative prose words (floats, equations, abstract, bibliography excluded): %d' % len(words))

# abstract alone
am = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', t, re.S)
ab = am.group(1)
ab = re.sub(r'\$[^$]*\$', ' X ', ab)
ab = re.sub(r'\\[a-zA-Z]+\*?', ' ', ab)
ab = re.sub(r'[{}~&\\]', ' ', ab)
abw = [w for w in re.split(r'\s+', ab) if re.search(r'[A-Za-z0-9]', w)]
print('   abstract words: %d  (MDPI limit: 200)' % len(abw))

# per-section prose
print('\n-- prose words per section --')
secs = list(re.finditer(r'\\section\{([^}]*)\}', t))
for i, m in enumerate(secs):
    seg = t[m.end():secs[i + 1].start() if i + 1 < len(secs) else len(t)]
    seg = re.sub(r'\\begin\{(table|figure|tabular|minipage|thebibliography)\}.*?\\end\{\1\}', ' ', seg, flags=re.S)
    seg = re.sub(r'\\begin\{thebibliography\}.*', ' ', seg, flags=re.S)
    seg = re.sub(r'\\begin\{(equation)\}.*?\\end\{\1\}', ' ', seg, flags=re.S)
    seg = re.sub(r'\$[^$]*\$', ' X ', seg)
    seg = re.sub(r'\\[a-zA-Z]+\*?(\[[^\]]*\])?', ' ', seg)
    seg = re.sub(r'[{}~&\\]', ' ', seg)
    w = [x for x in re.split(r'\s+', seg) if re.search(r'[A-Za-z0-9]', x)]
    print('   %-28s %5d' % (m.group(1)[:28], len(w)))

# --- forbidden terminology
print('\n-- terminology guard --')
for pat, note in [(r'grey[- ]box|gray[- ]box', 'grey-box'),
                  (r'DAgger', 'DAgger'),
                  (r'\bexpert\b', 'expert'),
                  (r'imitation', 'imitation'),
                  (r'\btwelve\b', 'twelve'),
                  (r'first in all four seasons', 'retracted seasonal claim'),
                  (r'only the raw library beats', 'retracted exclusivity claim')]:
    hits = [(t[:m.start()].count('\n') + 1, t[max(0, m.start() - 60):m.end() + 60].replace('\n', ' '))
            for m in re.finditer(pat, t, re.I)]
    print('   %-28s %d hit(s)' % (note, len(hits)))
    for ln, ctx in hits:
        print('        line ~%d: ...%s...' % (ln, ctx.strip()))

# --- unsourced markers
print('\n-- open markers --')
for pat in [r'\[UNSOURCED[^\]]*\]', r'\[[A-Z ]{4,}NEEDED\]', r'\[AUTHOR[^\]]*\]',
            r'\[AFFILIATION[^\]]*\]', r'\[CORRESPONDING[^\]]*\]', r'TODO', r'FIXME']:
    hits = list(re.finditer(pat, raw))
    if hits:
        print('   %-24s %d' % (pat, len(hits)))
