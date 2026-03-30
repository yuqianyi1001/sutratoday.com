
import sys

def cleanup(file_path, start_line, end_line):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    i = 0
    # Line indices are 0-based
    start_idx = start_line - 1
    end_idx = end_line - 1
    
    while i < len(lines):
        if i >= start_idx and i <= end_idx:
            # Special case for redundant header
            if i + 1 == 4393 and '### 现代语译' in lines[i] and i + 1 < len(lines) and '(待翻译)' in lines[i+1]:
                 i += 2 
                 continue
            
            if '(待翻译)' in lines[i]:
                cleaned = lines[i].replace('(待翻译)', '').strip()
                if cleaned:
                    new_lines.append(cleaned + '\n')
                i += 1
                continue
        
        new_lines.append(lines[i])
        i += 1
        
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    # Range covering blocks 448 to 494 and the redundant 447 marker
    cleanup('content/sutras/mulamadhyamakakarika.md', 4390, 4735)
