import os

def check_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    over_limit = []
    current_block = []
    in_original = False
    for i, line in enumerate(lines):
        if line.startswith('### 原文'):
            in_original = True
            current_block = []
        elif line.startswith('### 现代语译') or line.startswith('## '):
            if in_original:
                text = "".join(current_block).strip()
                if len(text) > 250:
                    over_limit.append((len(text), text))
                in_original = False
        elif in_original:
            current_block.append(line)
    return over_limit

for f in ['content/sutras/perfect-enlightenment-sutra.md', 'content/sutras/vimalakirti-sutra-01.md']:
    print(f"\nFile: {f}")
    for length, text in check_file(f):
        print(f"[{length}] {text[:100]}...")
