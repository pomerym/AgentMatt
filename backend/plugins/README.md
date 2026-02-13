# AgentMatt Plugin System

This directory contains Agno-compatible plugins for AgentMatt.

## Plugin Structure

Each plugin must be a Python module with:
- `plugin.json` - Plugin manifest (name, version, description, entry_point)
- `main.py` - Entry point with `register(agent)` function

## Example Plugin

```
my_plugin/
  plugin.json
  main.py
```

### plugin.json

```json
{
  "name": "my_plugin",
  "version": "1.0.0",
  "description": "Example Agno-compatible plugin",
  "entry_point": "main.py"
}
```

### main.py

```python
def register(agent):
    # Register tools, hooks, or UI components
    agent.register_tool("my_tool", my_tool_fn)
    agent.register_hook("on_message", my_hook_fn)
```

## Loading Plugins

Plugins are loaded automatically from this directory on startup.

