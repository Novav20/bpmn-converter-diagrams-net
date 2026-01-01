import json
import xml.etree.ElementTree as ET
import sys
import os

SYMBOLS_FILE = 'symbols.json'

def create_mx_file_structure():
    """Creates the basic Draw.io XML structure."""
    mxfile = ET.Element('mxfile', {
        'host': 'app.diagrams.net',
        'agent': 'BPMNConverter/1.0',
        'version': '21.0.0'
    })
    diagram = ET.SubElement(mxfile, 'diagram', {
        'name': 'BPMN Process',
        'id': 'generated_diagram_id'
    })
    # Typical grid and page settings
    model = ET.SubElement(diagram, 'mxGraphModel', {
        'dx': '1426', 'dy': '753', 'grid': '1', 'gridSize': '10', 
        'guides': '1', 'tooltips': '1', 'connect': '1', 'arrows': '1', 
        'fold': '1', 'page': '1', 'pageScale': '1', 'pageWidth': '850', 'pageHeight': '1100'
    })
    root = ET.SubElement(model, 'root')
    
    # Standard Layer 0 and 1
    ET.SubElement(root, 'mxCell', {'id': '0'})
    ET.SubElement(root, 'mxCell', {'id': '1', 'parent': '0'})
    
    return mxfile, root

def load_symbols():
    if not os.path.exists(SYMBOLS_FILE):
        raise FileNotFoundError(f"Symbols file {SYMBOLS_FILE} not found. Run extract_symbols.py first.")
    with open(SYMBOLS_FILE, 'r') as f:
        return json.load(f)

def generate_bpmn(input_data, output_file):
    symbols_registry = load_symbols()
    templates = symbols_registry.get('templates', {})
    modifiers = symbols_registry.get('modifiers', {})
    
    mxfile, root = create_mx_file_structure()
    
    nodes_map = {} # To track valid nodes for connections

    # 1. Process Nodes
    for el in input_data.get('elements', []):
        el_id = el.get('id')
        el_type = el.get('type')
        
        # Resolve Style
        style = ""
        width = 120
        height = 80
        
        if el_type in templates:
            tmpl = templates[el_type]
            style = tmpl.get('style_base', '')
            width = float(el.get('width', tmpl.get('width', 120)))
            height = float(el.get('height', tmpl.get('height', 80)))
            
            # Apply modifiers
            # Iterate through all properties of the element
            for key, val in el.items():
                if key in ['id', 'type', 'label', 'x', 'y', 'width', 'height']:
                    continue # Skip standard properties
                    
                if key in modifiers:
                    # Look up specific value modifier
                    # normalize val to string just in case
                    val_str = str(val)
                    if val_str in modifiers[key]:
                        mod_style = modifiers[key][val_str]
                        style += mod_style + ";"
                    else:
                        print(f"Warning: Value '{val}' for modifier '{key}' not found.")
        else:
            # Fallback
            print(f"Warning: Template type '{el_type}' not found. Using generic task.")
            style = "shape=mxgraph.bpmn.task2;rectStyle=rounded;size=10;html=1;whiteSpace=wrap;"
            width = float(el.get('width', 120))
            height = float(el.get('height', 80))

        # Determine parent
        parent_id = el.get('parent', '1')
        
        # Create Vertex
        cell = ET.SubElement(root, 'mxCell', {
            'id': el_id,
            'value': el.get('label', ''),
            'style': style,
            'parent': parent_id,
            'vertex': '1'
        })
        
        geo = ET.SubElement(cell, 'mxGeometry', {
            'x': str(el.get('x', 0)),
            'y': str(el.get('y', 0)),
            'width': str(width),
            'height': str(height),
            'as': 'geometry'
        })
        nodes_map[el_id] = True

    # 2. Process Connections
    for conn in input_data.get('connections', []):
        c_id = conn.get('id')
        source = conn.get('source')
        target = conn.get('target')
        
        if source not in nodes_map or target not in nodes_map:
            print(f"Warning: Connection {c_id} refers to missing nodes {source}->{target}")
            continue
            
        edge = ET.SubElement(root, 'mxCell', {
            'id': c_id,
            'value': conn.get('label', ''),
            'style': "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;",
            'edge': '1',
            'parent': '1',
            'source': source,
            'target': target
        })
        
        # Edge geometry
        geo = ET.SubElement(edge, 'mxGeometry', {'relative': '1', 'as': 'geometry'})
        
        # Waypoints
        if 'waypoints' in conn:
            points = ET.SubElement(geo, 'Array', {'as': 'points'})
            for wp in conn['waypoints']:
                ET.SubElement(points, 'mxPoint', {
                    'x': str(wp.get('x')),
                    'y': str(wp.get('y'))
                })

    # Write to file
    tree = ET.ElementTree(mxfile)
    ET.indent(tree, space="  ", level=0)
    tree.write(output_file, encoding='UTF-8', xml_declaration=True)
    print(f"Generated BPMN diagram at {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python bpmn_converter.py <input.json> <output.xml>")
        sys.exit(1)
        
    input_json_path = sys.argv[1]
    output_xml_path = sys.argv[2]
    
    try:
        with open(input_json_path, 'r') as f:
            data = json.load(f)
        generate_bpmn(data, output_xml_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
