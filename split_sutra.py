import re
import sys

def split_by_delimiters(text):
    delimiters = r'([。！？.!?；;，,])'
    parts = re.split(delimiters, text)
    res = []
    for i in range(0, len(parts) - 1, 2):
        res.append(parts[i] + parts[i+1])
    if len(parts) % 2 == 1:
        if parts[-1]:
            res.append(parts[-1])
    return res

def split_pair(orig_text, trans_text, limit=150):
    orig_text = orig_text.strip()
    trans_text = trans_text.strip()
    
    # Try splitting by paragraphs
    orig_paragraphs = orig_text.split('\n')
    trans_paragraphs = trans_text.split('\n')
    
    if len(orig_paragraphs) == len(trans_paragraphs) and len(orig_paragraphs) > 1:
        chunks_orig = []
        chunks_trans = []
        cur_orig = []
        cur_trans = []
        cur_len = 0
        for op, tp in zip(orig_paragraphs, trans_paragraphs):
            if cur_len + len(op) > limit and cur_orig:
                chunks_orig.append('\n'.join(cur_orig))
                chunks_trans.append('\n'.join(cur_trans))
                cur_orig = [op]
                cur_trans = [tp]
                cur_len = len(op)
            else:
                cur_orig.append(op)
                cur_trans.append(tp)
                cur_len += len(op)
        if cur_orig:
            chunks_orig.append('\n'.join(cur_orig))
            chunks_trans.append('\n'.join(cur_trans))
        return chunks_orig, chunks_trans
    
    # Try splitting by delimiters
    orig_parts = split_by_delimiters(orig_text)
    trans_parts = split_by_delimiters(trans_text)
    
    if len(orig_parts) == len(trans_parts) and len(orig_parts) > 1:
        chunks_orig = []
        chunks_trans = []
        cur_orig = []
        cur_trans = []
        cur_len = 0
        for os, ts in zip(orig_parts, trans_parts):
            if cur_len + len(os) > limit and cur_orig:
                chunks_orig.append(''.join(cur_orig))
                chunks_trans.append(''.join(cur_trans))
                cur_orig = [os]
                cur_trans = [ts]
                cur_len = len(os)
            else:
                cur_orig.append(os)
                cur_trans.append(ts)
                cur_len += len(os)
        if cur_orig:
            chunks_orig.append(''.join(cur_orig))
            chunks_trans.append(''.join(cur_trans))
        return chunks_orig, chunks_trans

    # Force split if still too long
    # Find a punctuation near the middle of orig_text
    mid_orig = len(orig_text) // 2
    split_orig = -1
    for p in "。！？；，.!?;,":
        # Search around the middle
        pos = orig_text.find(p, mid_orig - 50)
        if pos != -1 and pos < mid_orig + 100:
            split_orig = pos
            break
    
    if split_orig == -1:
        # Just split at mid
        split_orig = mid_orig

    # Try to find a similar punctuation in trans_text near its relative position
    ratio = split_orig / len(orig_text)
    mid_trans = int(len(trans_text) * ratio)
    split_trans = -1
    for p in "。！？；，.!?;,":
        pos = trans_text.find(p, mid_trans - 50)
        if pos != -1 and pos < mid_trans + 100:
            split_trans = pos
            break
    
    if split_trans == -1:
        split_trans = mid_trans
        
    return [orig_text[:split_orig+1].strip(), orig_text[split_orig+1:].strip()], \
           [trans_text[:split_trans+1].strip(), trans_text[split_trans+1:].strip()]

def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    fm_match = re.match(r'^(---\n.*?\n---)(.*)', content, re.DOTALL)
    if not fm_match: return
    
    front_matter = fm_match.group(1)
    body = fm_match.group(2)

    markers = list(re.finditer(r'### (原文|现代语译)', body))
    
    new_body = ""
    last_pos = 0
    
    i = 0
    while i < len(markers):
        marker = markers[i]
        m_type = marker.group(1)
        new_body += body[last_pos:marker.start()]
        
        if m_type == '原文':
            if i + 1 < len(markers) and markers[i+1].group(1) == '现代语译':
                trans_marker = markers[i+1]
                orig_start = body.find('\n', marker.end()) + 1
                orig_text = body[orig_start:trans_marker.start()]
                
                trans_start = body.find('\n', trans_marker.end()) + 1
                trans_end = markers[i+2].start() if i + 2 < len(markers) else len(body)
                trans_text = body[trans_start:trans_end]
                
                if len(orig_text.strip()) > 250:
                    chunks_orig, chunks_trans = split_pair(orig_text, trans_text)
                    # Recursive split for very long blocks
                    while any(len(c) > 250 for c in chunks_orig):
                        new_chunks_orig = []
                        new_chunks_trans = []
                        for co, ct in zip(chunks_orig, chunks_trans):
                            if len(co) > 250:
                                so, st = split_pair(co, ct)
                                new_chunks_orig.extend(so)
                                new_chunks_trans.extend(st)
                            else:
                                new_chunks_orig.append(co)
                                new_chunks_trans.append(ct)
                        chunks_orig = new_chunks_orig
                        chunks_trans = new_chunks_trans
                        
                    for co, ct in zip(chunks_orig, chunks_trans):
                        new_body += f"### 原文\n{co.strip()}\n\n### 现代语译\n{ct.strip()}\n\n"
                else:
                    new_body += f"### 原文\n{orig_text.strip()}\n\n### 现代语译\n{trans_text.strip()}\n\n"
                
                last_pos = trans_end
                i += 2
                continue
        
        new_body += marker.group(0)
        last_pos = marker.end()
        i += 1
    
    new_body += body[last_pos:]

    with open(file_path, 'w', encoding='utf-8') as f:
        final_content = front_matter + "\n" + new_body
        final_content = re.sub(r'\n{3,}', '\n\n', final_content)
        f.write(final_content.strip() + '\n')

process_file('content/sutras/srimala-sutra.md')
