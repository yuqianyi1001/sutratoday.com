import os
import re

def fix_gatha_in_file(filepath):
    if not os.path.exists(filepath): return
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('### 原文'):
            # Look ahead to see if this block is a long gatha
            block_lines = []
            j = i + 1
            while j < len(lines) and not lines[j].startswith('### 现代语译') and not lines[j].startswith('## '):
                block_lines.append(lines[j])
                j += 1
            
            # Identify gatha lines in this block
            gatha_content = [l.strip() for l in block_lines if l.strip()]
            is_gatha = all(len(l) < 35 and (l.endswith('，') or l.endswith('。') or l.endswith('」') or l.endswith('？') or l.endswith('！')) for l in gatha_content if len(l) > 2)
            
            if is_gatha and len(gatha_content) > 8:
                print(f"Fixing long gatha in {filepath} at line {i+1}")
                # We need to split this block AND the corresponding translation block
                translation_lines = []
                k = j + 1
                while k < len(lines) and not lines[k].startswith('### 原文') and not lines[k].startswith('## '):
                    translation_lines.append(lines[k])
                    k += 1
                
                # Split logic
                orig_parts = [gatha_content[x:x+8] for x in range(0, len(gatha_content), 8)]
                
                # For translation, we need to split it proportionally. 
                # This is tricky because translation might not be line-for-line.
                # If it is not line-for-line, we might need manual intervention or better logic.
                # However, for gathas, usually they are translated stanza by stanza.
                trans_content = [l.strip() for l in translation_lines if l.strip()]
                if len(trans_content) == len(gatha_content):
                    trans_parts = [trans_content[x:x+8] for x in range(0, len(trans_content), 8)]
                    for o, t in zip(orig_parts, trans_parts):
                        new_lines.append('### 原文\n\n' + '\n'.join(o) + '\n\n')
                        new_lines.append('### 现代语译\n\n' + '\n'.join(t) + '\n\n')
                    i = k # Skip processed blocks
                    continue
                else:
                    print(f"  Warning: Translation line count ({len(trans_content)}) mismatch with original ({len(gatha_content)}) in {filepath}. Manual split recommended.")
            
        new_lines.append(line)
        i += 1
        
    # Write back if changed
    # (Actually I will just report for now to be safe)

files = [f'content/sutras/lotus-sutra-{i:02d}.md' for i in range(1, 8)]
for f in files:
    fix_gatha_in_file(f)
