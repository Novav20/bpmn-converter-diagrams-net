import os
import xml.etree.ElementTree as ET
import json
import re

ASSETS_DIR = 'assets'
OUTPUT_FILE = 'symbols.json'

# Base style definitions to identify major categories and create templates
TEMPLATES = {
    # Tasks usually have shape=mxgraph.bpmn.task2 or similar, and specific sizes
    'task': {
        'match_criteria': lambda s: 'shape=mxgraph.bpmn.task2' in s,
        'properties': {
            'width': 120,
            'height': 80,
            'vertex': "1",
            'style_base': "shape=mxgraph.bpmn.task2;rectStyle=rounded;size=10;html=1;container=1;collapsible=0;expand=0;points=[[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0.25,0],[1,0.5,0],[1,0.75,0],[0.75,1,0],[0.5,1,0],[0.25,1,0],[0,0.75,0],[0,0.5,0],[0,0.25,0]];"
        }
    },
    'event': {
        'match_criteria': lambda s: 'shape=mxgraph.bpmn.event' in s,
        'properties': {
            'width': 50,
            'height': 50,
            'vertex': "1",
            'style_base': "shape=mxgraph.bpmn.event;html=1;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;verticalAlign=top;align=center;perimeter=ellipsePerimeter;outlineConnect=0;aspect=fixed;points=[[0.145,0.145,0],[0.5,0,0],[0.855,0.145,0],[1,0.5,0],[0.855,0.855,0],[0.5,1,0],[0.145,0.855,0],[0,0.5,0]];"
        }
    },
    'gateway': {
        'match_criteria': lambda s: 'shape=mxgraph.bpmn.gateway2' in s,
        'properties': {
            'width': 60,
            'height': 60,
            'vertex': "1",
            'style_base': "shape=mxgraph.bpmn.gateway2;html=1;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;verticalAlign=top;align=center;perimeter=rhombusPerimeter;outlineConnect=0;verticalAlign=top;align=center;points=[[0.25,0.25,0],[0.5,0,0],[0.75,0.25,0],[1,0.5,0],[0.75,0.75,0],[0.5,1,0],[0.25,0.75,0],[0,0.5,0]];"
        }
    },
     'data_object': {
        'match_criteria': lambda s: 'shape=mxgraph.bpmn.data2' in s,
        'properties': {
             'width': 40,
             'height': 60,
             'vertex': "1",
             'style_base': "shape=mxgraph.bpmn.data2;labelPosition=center;verticalLabelPosition=bottom;align=center;verticalAlign=top;size=15;html=1;"
        }
    },
    'sub_process': { 
        'match_criteria': lambda s: 'swimlane' in s.lower() and ('childLayout' in s or 'stackLayout' in s),
        'properties': {
            'vertex': "1",
             'style_base': "swimlane;html=1;childLayout=stackLayout;resizeParent=1;resizeParentMax=0;startSize=20;"
        }
    },
    'pool': {
        'match_criteria': lambda s: 'swimlane' in s.lower() and 'childLayout' in s,
        'properties': {
            'width': 600,
            'height': 400,
            'vertex': "1",
            'style_base': "swimlane;html=1;childLayout=stackLayout;resizeParent=1;resizeParentMax=0;startSize=20;horizontal=0;whiteSpace=wrap;"
        }
    },
    'lane': {
        'match_criteria': lambda s: 'swimlane' in s.lower() and 'childLayout' not in s and 'stackLayout' not in s,
        'properties': {
            'width': 600,
            'height': 120,
            'vertex': "1",
            'style_base': "swimlane;html=1;startSize=20;horizontal=0;"
        }
    }
}

def parse_style(style_str):
    """Parses a style string into a dictionary."""
    if not style_str:
        return {}
    style_dict = {}
    tokens = style_str.split(';')
    for token in tokens:
        if '=' in token:
            key, value = token.split('=', 1)
            style_dict[key] = value
        elif token:
             style_dict[token] = None # Flag style like 'rounded'
    return style_dict

def dict_to_style(style_dict):
    """Reconstructs a style string from a dictionary."""
    parts = []
    for k, v in style_dict.items():
        if v is not None:
             parts.append(f"{k}={v}")
        else:
             parts.append(k)
    return ';'.join(parts) + (';' if parts else '')

def extract_symbols():
    symbols_registry = {
        "templates": {},
        "modifiers": {}
    }
    
    # Register templates in output
    for key, tmpl in TEMPLATES.items():
        symbols_registry["templates"][key] = tmpl['properties']

    processed_count = 0
    
    for filename in os.listdir(ASSETS_DIR):
        if not filename.endswith('.xml'):
            continue
            
        filepath = os.path.join(ASSETS_DIR, filename)
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # Find the diagram root
            # Note: The structure is mxfile -> diagram -> mxGraphModel -> root -> mxCell
            graph_model = root.find('.//mxGraphModel')
            if graph_model is None:
                continue
            
            mx_root = graph_model.find('root')
            if mx_root is None:
                continue

            for cell in mx_root.findall('mxCell'):
                style = cell.get('style')
                if not style:
                    continue

                width = cell.find('mxGeometry').get('width') if cell.find('mxGeometry') is not None else None
                height = cell.find('mxGeometry').get('height') if cell.find('mxGeometry') is not None else None
                
                # Identify Template
                matched_template = None
                for tmpl_name, tmpl_data in TEMPLATES.items():
                    if tmpl_data['match_criteria'](style):
                        matched_template = tmpl_name
                        break
                
                if matched_template:
                    # Parse full style and base style to find delta
                    current_style_dict = parse_style(style)
                    base_style_dict = parse_style(TEMPLATES[matched_template]['properties'].get('style_base', ''))
                    
                    # Identify Modifiers
                    for k, v in current_style_dict.items():
                        # We only care if the key is NOT in base style OR value is different
                        if k not in base_style_dict or base_style_dict[k] != v:
                            # This is a potential modifier
                            # We record it in the registry: modifiers[key][value] = "key=value"
                            if k not in symbols_registry["modifiers"]:
                                symbols_registry["modifiers"][k] = {}
                            
                            val_key = v if v is not None else "default" # "default" for flags like 'rounded'
                            
                            # Construct the style fragment
                            style_fragment = f"{k}={v}" if v is not None else k
                            
                            symbols_registry["modifiers"][k][val_key] = style_fragment
                    
                    processed_count += 1

        except Exception as e:
            print(f"Error processing {filename}: {e}")

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(symbols_registry, f, indent=2)
    
    print(f"Extracted {processed_count} symbols to {OUTPUT_FILE}")

if __name__ == "__main__":
    try:
        extract_symbols()
    except Exception as e:
        with open("debug.log", "w") as search:
            import traceback
            traceback.print_exc(file=search)
            search.write(str(e))
        print(f"FAILED: {e}")
