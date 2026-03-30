import xml.etree.ElementTree as ET

def debug_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {'tei': 'http://www.tei-c.org/ns/1.0', 'cb': 'http://www.cbeta.org/ns/1.0'}
    
    print(f"ROOT TAG: {root.tag}")
    for div in root.findall(".//tei:div", ns):
        print(f"DIV TYPE: {div.get('type')}, ID: {div.get('{http://www.w3.org/XML/1998/namespace}id')}")

if __name__ == "__main__":
    debug_xml("sources/cbeta/T15n0602_001.xml")
