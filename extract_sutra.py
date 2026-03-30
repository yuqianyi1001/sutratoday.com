import xml.etree.ElementTree as ET
import re
from opencc import OpenCC

def extract_sutra(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {'tei': 'http://www.tei-c.org/ns/1.0', 'cb': 'http://www.cbeta.org/ns/1.0'}
    
    cc = OpenCC('t2s') # Traditional to Simplified

    def get_text(node):
        if node.tag in [f"{{{ns['tei']}}}note", f"{{{ns['cb']}}}note", f"{{{ns['tei']}}}anchor", f"{{{ns['tei']}}}lb", f"{{{ns['tei']}}}pb", f"{{{ns['tei']}}}milestone"]:
            return ""
        
        # Keep track of where we are to avoid double counting if we are traversing sub-elements
        text = node.text if node.text else ""
        for child in node:
            if child.tag == f"{{{ns['tei']}}}app":
                lem = child.find(f"{{{ns['tei']}}}lem", ns)
                if lem is not None:
                    text += get_text(lem)
            elif child.tag == f"{{{ns['tei']}}}rdg":
                continue
            elif child.tag == f"{{{ns['tei']}}}p":
                # If we are already inside a p, we might not want to recurse here 
                # but CBETA XML often has p inside div, not p inside p.
                text += get_text(child)
            else:
                text += get_text(child)
            
            if child.tail:
                text += child.tail
        return text

    content = []
    body = root.find(".//tei:text/tei:body", ns)
    
    def process_node(node):
        if node.tag == f"{{{ns['tei']}}}milestone":
            n = node.get('n')
            if n == '1':
                content.append(("CHAPTER", "卷上"))
            elif n == '2':
                content.append(("CHAPTER", "卷下"))
        elif node.tag == f"{{{ns['tei']}}}p":
            text = get_text(node).strip()
            text = re.sub(r'\s+', '', text)
            if text:
                segments = []
                while len(text) > 250:
                    break_point = 250
                    for punc in "。！？；":
                        idx = text.rfind(punc, 0, 250)
                        if idx != -1:
                            break_point = idx + 1
                            break
                    segments.append(text[:break_point])
                    text = text[break_point:]
                if text:
                    segments.append(text)
                for seg in segments:
                    content.append(("PARAGRAPH", cc.convert(seg)))
        else:
            for child in node:
                process_node(child)

    process_node(body)
    return content

if __name__ == "__main__":
    result = extract_sutra("sources/cbeta/T17n0839_001.xml")
    for type, text in result:
        print(f"{type}|{text}")
