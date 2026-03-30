import re

# Simple traditional to simplified conversion for common characters
# This is a small subset, I will use my own knowledge for the rest during the process.
# But for the whole text, I should be careful.
# I'll just use my internal translation capability segment by segment.

def segment_text(text, limit=250):
    # Split by punctuation to avoid cutting in the middle of a sentence
    # CBETA text has full-width punctuation
    sentences = re.split(r'([。？！；])', text)
    segments = []
    current_seg = ""
    for i in range(0, len(sentences)-1, 2):
        s = sentences[i] + sentences[i+1]
        if len(current_seg) + len(s) > limit:
            if current_seg:
                segments.append(current_seg)
            current_seg = s
        else:
            current_seg += s
    if current_seg:
        segments.append(current_seg)
    return segments

# I'll manually process the first few segments to show progress.
