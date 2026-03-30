import json

with open('translations.json', 'r') as f:
    translations = json.load(f)

with open('content/sutras/mulamadhyamakakarika.md', 'r') as f:
    lines = f.readlines()

final_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith("### 原文"):
        final_lines.append(line)
        i += 1
        content_lines = []
        while i < len(lines) and not lines[i].startswith("### 现代语译"):
            content_lines.append(lines[i])
            final_lines.append(lines[i])
            i += 1
        
        content = "".join(content_lines).strip()
        
        if i < len(lines) and lines[i].startswith("### 现代语译"):
            final_lines.append(lines[i])
            i += 1
            if content in translations:
                final_lines.append(translations[content] + "\n")
                # Skip existing (待翻译) and empty lines
                while i < len(lines) and ( "(待翻译)" in lines[i] or lines[i].strip() == "" ):
                    i += 1
            else:
                # Not a target block, keep original (待翻译) if any
                pass
    else:
        final_lines.append(line)
        i += 1

with open('content/sutras/mulamadhyamakakarika.md', 'w') as f:
    f.writelines(final_lines)
