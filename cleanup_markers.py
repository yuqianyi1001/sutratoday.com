
import sys

def remove_specific_lines(file_path, line_numbers):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # line_numbers are 1-based
    new_lines = []
    line_set = set(line_numbers)
    for i, line in enumerate(lines):
        if (i + 1) in line_set:
            if '(待翻译)' in line:
                # Remove just the "(待翻译)" part or the whole line if it's only that
                cleaned = line.replace('(待翻译)', '').strip()
                if cleaned:
                    new_lines.append(cleaned + '\n')
                # If it's empty, we don't append anything, effectively removing the line
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    # Line numbers of (待翻译) for blocks 448 to 494
    # From grep output earlier:
    lines_to_clean = [
        4408, 4415, 4422, 4429, 4436, 4443, 4450, 4457, 4464, 4471, 
        4478, 4485, 4492, 4499, 4506, 4513, 4520, 4527, 4534, 4541, 
        4548, 4555, 4562, 4569, 4576, 4583, 4590, 4597, 4604, 4611, 
        4618, 4625, 4632, 4639, 4646, 4653, 4660, 4667, 4674, 4681, 
        4688, 4695, 4702, 4709, 4716, 4723, 4730
    ]
    remove_specific_lines('content/sutras/mulamadhyamakakarika.md', lines_to_clean)
