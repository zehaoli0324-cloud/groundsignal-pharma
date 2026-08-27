# -*- coding: utf-8 -*-
"""Fix demo vault: downgrade wikilinks pointing outside demo to plain text."""
import os, re

BASE = "/home/zehaoli0324/projects/groundsignal-pharma/demo"

files = {os.path.splitext(f)[0] for root, _, fs in os.walk(BASE)
         if '.obsidian' not in root for f in fs if f.endswith('.md')}

fixed = 0
for root, _, fs in os.walk(BASE):
    if '.obsidian' in root:
        continue
    for f in fs:
        if not f.endswith('.md'):
            continue
        p = os.path.join(root, f)
        text = open(p, encoding='utf-8').read()
        changed = False
        def repl(m):
            global fixed
            target = m.group(1).split('|')[0].split('#')[0].strip()
            if target and os.path.basename(target) not in files:
                fixed += 1
                return target
            return m.group(0)
        new_text = re.sub(r'\[\[([^\]]+)\]\]', repl, text)
        if new_text != text:
            open(p, 'w', encoding='utf-8').write(new_text)
            changed = True
        if changed:
            print('fixed:', p)

print('total downgraded:', fixed)
