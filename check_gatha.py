import os
import re

files = [
    'content/sutras/renwang-sutra-01.md', 'content/sutras/renwang-sutra-02.md',
    'content/sutras/fanwang-sutra-01.md', 'content/sutras/fanwang-sutra-02.md'
] + [f'content/sutras/golden-light-sutra-{i:02d}.md' for i in range(1, 11)]

def check_gatha_lengths(filepath):
    if not os.path.exists(filepath): return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all 原文 blocks
    blocks = re.findall(r'### 原文\n(.*?)\n### 现代语译', content, re.DOTALL)
    for i, block in enumerate(blocks):
        lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
        # Count lines that look like gatha (short, ending in punctuation)
        gatha_lines = [l for l in lines if len(l) < 30 and (l.endswith('，') or l.endswith('。') or l.endswith('」') or l.endswith('？'))]
        if len(gatha_lines) > 8:
            print(f"File: {filepath}, Block {i+1} has {len(gatha_lines)} gatha lines.")

for f in files:
    check_gatha_lengths(f)
