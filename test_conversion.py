import json
import os
import subprocess
import xml.etree.ElementTree as ET

INPUT_JSON = 'test_input.json'
OUTPUT_XML = 'test_output.drawio.xml'

def create_sample_input():
    # Based on what we likely have in symbols.json
    data = {
        "elements": [
            {
                "id": "start_event",
                "type": "event", 
                "label": "Start",
                "symbol": "general",
                "x": 100,
                "y": 100
            },
            {
                "id": "task_1",
                "type": "task",
                "taskMarker": "user",
                "label": "User Task",
                "x": 200,
                "y": 100
            },
            {
                "id": "end_event",
                "type": "event",
                "symbol": "terminate",
                "label": "Terminate",
                "x": 400,
                "y": 100
            }
        ],
        "connections": [
            {
                "id": "flow_1",
                "source": "start_event",
                "target": "task_1",
                "label": ""
            },
            {
                "id": "flow_2",
                "source": "task_1",
                "target": "end_event",
                "label": "Done"
            }
        ]
    }
    with open(INPUT_JSON, 'w') as f:
        json.dump(data, f, indent=2)

def run_test():
    print("Creating sample input...")
    create_sample_input()
    
    print("Running converter...")
    result = subprocess.run(['python3', 'bpmn_converter.py', INPUT_JSON, OUTPUT_XML], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Converter failed!")
        print(result.stderr)
        return False
        
    print("Converter finished. Verifying output...")
    if not os.path.exists(OUTPUT_XML):
        print("Output file not found!")
        return False
        
    try:
        tree = ET.parse(OUTPUT_XML)
        root = tree.getroot()
        # Namespace might be an issue if there is one, but standard ElementTree handles no-namespace XML fine
        
        # Check for cells
        cells = root.findall('.//mxCell')
        print(f"Found {len(cells)} cells.")
        
        ids = [c.get('id') for c in cells]
        if 'start_event' in ids and 'task_1' in ids and 'flow_1' in ids:
            print("SUCCESS: Found expected elements in XML.")
            return True
        else:
            print(f"FAILURE: Missing elements. Found IDs: {ids}")
            return False
            
    except Exception as e:
        print(f"XML Parsing failed: {e}")
        return False

if __name__ == "__main__":
    if run_test():
        print("TEST PASSED")
    else:
        print("TEST FAILED")
