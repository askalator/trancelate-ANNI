"""
Shared trace functionality with append-only behavior.
Guarantees no overwriting of trace data.
"""

from typing import Dict, Any

def t(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get trace dictionary from context, creating if needed.
    
    Returns:
        ctx.setdefault("trace", {})
    """
    return ctx.setdefault("trace", {})

def push(ctx: Dict[str, Any], key: str, entry: Dict[str, Any]) -> None:
    """
    Append entry to trace list, creating list if needed.
    
    Guarantees append-only behavior.
    """
    trace = t(ctx)
    if key not in trace:
        trace[key] = []
    trace[key].append(entry)
