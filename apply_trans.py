import re
import json
import sys

def apply_translations(file_path, json_paths):
    with open(file_path, 'r') as f:
        content = f.read()
    
    all_translations = {}
    for j_path in json_paths:
        with open(j_path, 'r') as f:
            all_translations.update(json.load(f))
    
    # Split the content into blocks. Each block starts with ### 原文 and contains the following ### 现代语译
    # The structure is:
    # ### 原文
    # ...
    # ### 现代语译
    # (empty space)
    # ### 原文 ...
    
    # We can split by '### 现代语译\n' and then for each resulting part, 
    # the part before the split is '### 原文 ...', and we insert the translation after the split.
    
    parts = content.split('### 现代语译\n')
    # parts[0] is everything before first '### 现代语译\n'
    # parts[1] is everything between first and second '### 现代语译\n'
    
    new_content = parts[0]
    for i in range(1, len(parts)):
        new_content += '### 现代语译\n'
        # The translation for segment i
        trans = all_translations.get(str(i), "").strip()
        new_content += trans + "\n\n"
        
        # Now we need to add the rest of parts[i], but skip the initial newlines if any
        rest = parts[i].lstrip('\n')
        new_content += rest
        
    with open(file_path, 'w') as f:
        f.write(new_content)

if __name__ == "__main__":
    apply_translations(sys.argv[1], sys.argv[2:])
