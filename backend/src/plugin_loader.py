"""
AgentMatt Plugin Loader

Loads Agno-compatible plugins from the plugins directory.
"""

import os
import json
import importlib.util

PLUGINS_DIR = os.path.join(os.path.dirname(__file__), '../plugins')

loaded_plugins = []

def load_plugin(plugin_path):
    """Load a single plugin from its directory."""
    manifest_path = os.path.join(plugin_path, 'plugin.json')
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path) as f:
        manifest = json.load(f)
    entry_point = os.path.join(plugin_path, manifest.get('entry_point', 'main.py'))
    if not os.path.exists(entry_point):
        return None
    spec = importlib.util.spec_from_file_location(manifest['name'], entry_point)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {
        'manifest': manifest,
        'module': module
    }

def load_all_plugins():
    """Load all plugins from the plugins directory."""
    global loaded_plugins
    loaded_plugins = []
    if not os.path.isdir(PLUGINS_DIR):
        return loaded_plugins
    for name in os.listdir(PLUGINS_DIR):
        plugin_path = os.path.join(PLUGINS_DIR, name)
        if os.path.isdir(plugin_path):
            plugin = load_plugin(plugin_path)
            if plugin:
                loaded_plugins.append(plugin)
    return loaded_plugins

def get_loaded_plugins():
    """Return list of loaded plugins."""
    return loaded_plugins

def register_plugins(agent):
    """Register all loaded plugins with the agent."""
    for plugin in loaded_plugins:
        module = plugin['module']
        if hasattr(module, 'register'):
            module.register(agent)
