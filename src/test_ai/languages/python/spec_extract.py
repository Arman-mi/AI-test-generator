import json
from typing import Optional, Dict, Any


MARKER  = "@testai_json:"

def extract_testai_json(docstring: Optional[str]) ->Optional[Dict[str,Any]]:
    """
    Extract and parse the JSON block following '@testai_json:' in a docstring.

    Returns:
        dict if found
        None if no marker
    Raises:
        ValueError if marker exists but JSON is invalid
    """
    if not docstring:
        return None
    marker_index = docstring.find(MARKER)

    if marker_index == -1:
        return None
    after_marker = docstring[marker_index + len(MARKER):].strip()
    if not after_marker:
        raise ValueError("Found @testai tag but no content after it :((")
    

    start, end = after_marker.find("{"), after_marker.rfind("}")


    if start == -1 or end ==-1 or end < start:
        raise ValueError("could not find a valid json after @test_ai tag :((")
    

    json_text = after_marker[start:end + 1]

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in @testai_json block: {e}") from e
    
    if not isinstance(data,dict):
        raise ValueError("@testai must contain a JSON object")
    
    return data
