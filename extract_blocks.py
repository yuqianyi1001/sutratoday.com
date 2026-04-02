
import re

file_path = '/Users/j.wu/ws/codex_anything/content/sutras-raw/T0221-009.md'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Split by segments
segments = re.split(r'### (原文|现代语译)', content)

# segments[0] is frontmatter and title
# Then we have pairs of (type, content)
# segments[1] is '原文' or '现代语译', segments[2] is the text
# and so on.

headers = segments[0]
raw_blocks = []
for i in range(1, len(segments), 2):
    if segments[i] == '原文':
        raw_blocks.append(segments[i+1].strip())

print(f"Found {len(raw_blocks)} 原文 blocks.")

with open('raw_blocks.txt', 'w', encoding='utf-8') as f:
    for block in raw_blocks:
        f.write(block + '\n---BLOCK_END---\n')
