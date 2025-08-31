"""
Shared HTTP client functionality using urllib.
"""

import urllib.request
import urllib.parse
import json
from typing import Tuple, Dict, Any

def json_get(url: str, timeout: float = 5.0) -> Tuple[int, Dict[str, Any]]:
    """
    Perform GET request and return JSON response.
    
    Returns:
        (status_code, response_dict)
    """
    try:
        req = urllib.request.Request(url)
        req.add_header('Connection', 'close')
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            response_data = json.loads(response.read().decode('utf-8'))
            return status_code, response_data
    except Exception as e:
        return 500, {"error": str(e)}

def json_post(url: str, obj: Dict[str, Any], timeout: float = 60.0) -> Tuple[int, Dict[str, Any]]:
    """
    Perform POST request with JSON data.
    
    Returns:
        (status_code, response_dict)
    """
    try:
        data = json.dumps(obj).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Connection', 'close')
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            response_data = json.loads(response.read().decode('utf-8'))
            return status_code, response_data
    except Exception as e:
        return 500, {"error": str(e)}
