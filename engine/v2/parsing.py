"""
V2 Parsing Utilities
JSON response parsing for LLM outputs.
"""

import json
import re
from typing import Any, Dict, Tuple, Optional


def extract_json_from_markdown(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract and parse JSON from a markdown code block.
    
    Args:
        response: Raw response that may contain markdown JSON block
        
    Returns:
        Parsed JSON dict or None if parsing fails
    """
    try:
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response
        
        parsed = json.loads(json_str)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, Exception):
        pass
    
    return None


def parse_json_response(response: str, main_field: str, summary_field: str, 
                        fallback: str = "") -> Tuple[str, str]:
    """
    Parse JSON response to extract main content and summary.
    
    Args:
        response: The raw LLM response (may contain markdown code blocks)
        main_field: The field name for the main content
        summary_field: The field name for the summary/actionables
        fallback: Value to use if parsing fails
        
    Returns:
        Tuple of (main_content, summary)
    """
    parsed = extract_json_from_markdown(response)
    
    if parsed is not None:
        main_content = parsed.get(main_field, fallback)
        summary = parsed.get(summary_field, "")
    else:
        main_content = fallback
        summary = ""
    
    return main_content, summary
