import re

with open('content/sutras/mulamadhyamakakarika.md', 'r') as f:
    lines = f.readlines()

markers = []
for i, line in enumerate(lines):
    if "(待翻译)" in line:
        markers.append(i)

# markers[700] is the 701st marker (0-indexed)
# markers[799] is the 800th marker
start_idx = markers[700]
end_idx = markers[799]

print(f"Start Line: {start_idx + 1}")
print(f"End Line: {end_idx + 1}")

# Extract sections
# For each marker, find its corresponding ### 原文
# Since one ### 原文 might have multiple (待翻译) markers, we group them.

target_markers = markers[700:800]
print(f"Total markers in target: {len(target_markers)}")

# Let's find unique ### 原文 blocks for these markers
unique_blocks = []
current_block = None

for m_idx in target_markers:
    # Look backwards from m_idx to find the nearest ### 原文
    found_header = False
    for i in range(m_idx - 1, -1, -1):
        if lines[i].startswith("### 原文"):
            header_line = i
            found_header = True
            break
    
    if found_header:
        if current_block is None or current_block['header'] != header_line:
            if current_block:
                unique_blocks.append(current_block)
            current_block = {
                'header': header_line,
                'markers': [m_idx]
            }
        else:
            current_block['markers'].append(m_idx)

if current_block:
    unique_blocks.append(current_block)

print(f"Total unique ### 原文 blocks: {len(unique_blocks)}")

for i, block in enumerate(unique_blocks):
    header_line = block['header']
    # Get content between ### 原文 and next ### 现代语译
    content_lines = []
    for j in range(header_line + 1, len(lines)):
        if lines[j].startswith("### 现代语译"):
            break
        content_lines.append(lines[j])
    
    content = "".join(content_lines).strip()
    print(f"\nBlock {i+1} (Header Line {header_line + 1}):")
    print(content)
    print("-" * 20)
