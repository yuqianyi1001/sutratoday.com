
import re
import json

file_path = 'content/sutras-raw/T0221-011.md'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Using a more robust split to keep track of the structure
parts = re.split(r'(### 原文\n\n|### 现代语译\n\n)', content)

# parts[0] is everything before the first '### 原文\n\n'
# then parts[1] is '### 原文\n\n', parts[2] is the text, parts[3] is '### 现代语译\n\n', parts[4] is the text (often empty)

raw_segments = []
for i in range(1, len(parts), 4):
    if i+1 < len(parts):
        raw_segments.append(parts[i+1].strip())

print(f"Total segments found: {len(raw_segments)}")

with open('extracted_segments_011.json', 'w', encoding='utf-8') as f:
    json.dump(raw_segments, f, ensure_ascii=False, indent=2)
