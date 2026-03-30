import xml.etree.ElementTree as ET
import re

def extract_text(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Namespace handling
    ns = {'tei': 'http://www.tei-c.org/ns/1.0', 'cb': 'http://www.cbeta.org/ns/1.0'}
    
    def walk(node):
        # Ignore notes and other non-text elements
        if node.tag in [f"{{{ns['tei']}}}note", f"{{{ns['cb']}}}note", f"{{{ns['tei']}}}anchor", f"{{{ns['tei']}}}lb", f"{{{ns['tei']}}}pb", f"{{{ns['tei']}}}milestone"]:
            return ""
            
        # Also ignore mu-lu (Table of Contents)
        if node.tag == f"{{{ns['cb']}}}mulu":
            return ""

        text = node.text if node.text else ""
        
        for child in node:
            if child.tag == f"{{{ns['tei']}}}app":
                lem = child.find(f"{{{ns['tei']}}}lem", ns)
                if lem is not None:
                    text += walk(lem)
            elif child.tag == f"{{{ns['tei']}}}rdg":
                continue
            else:
                text += walk(child)
            
            if child.tail:
                text += child.tail
                
        return text

    content = []
    
    # Find all cb:divs
    divs = root.findall(".//cb:div", ns)
    for div in divs:
        div_type = div.get('type')
        if div_type == 'xu':
            text = walk(div).strip()
            text = re.sub(r'\s+', '', text)
            content.append(("序", "康僧会序", text))
        elif div_type == 'jing':
            text = walk(div).strip()
            text = re.sub(r'\s+', '', text)
            content.append(("经", "佛说大安般守意经", text))
            
    return content

if __name__ == "__main__":
    result = extract_text("sources/cbeta/T15n0602_001.xml")
    for type, title, text in result:
        print(f"TITLE: {title}")
        print(f"LEN: {len(text)}")
        print(f"START: {text[:100]}")
        print("---")
