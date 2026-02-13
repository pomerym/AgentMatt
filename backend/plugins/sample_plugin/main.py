"""
Sample Plugin

A sample Agno-compatible plugin for testing the plugin loader.
"""

def sample_tool(text):
    """A simple tool that returns reversed text."""
    return text[::-1]

def sample_hook(message):
    """A simple hook that logs messages."""
    print(f"Sample hook triggered: {message}")
    return {"hook": "sample_hook", "message": message}

def register(agent):
    """Register the plugin with the agent."""
    agent.register_tool("sample_reverse", sample_tool)
    agent.register_hook("on_message", sample_hook)
    agent.remember({"plugin": "sample_plugin", "status": "loaded"})
