"""
AgentMatt Agent Core

Provides the Agent class with tool, hook, and memory registration for Agno compatibility.
"""

class Agent:
    def __init__(self):
        self.tools = {}
        self.hooks = {}
        self.memory = []

    def register_tool(self, name, fn):
        """Register a tool function by name."""
        self.tools[name] = fn

    def register_hook(self, event, fn):
        """Register a hook function for an event."""
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(fn)

    def call_tool(self, name, *args, **kwargs):
        """Call a registered tool by name."""
        if name in self.tools:
            return self.tools[name](*args, **kwargs)
        raise ValueError(f"Tool '{name}' not found")

    def trigger_hook(self, event, *args, **kwargs):
        """Trigger all hooks for an event."""
        results = []
        for fn in self.hooks.get(event, []):
            results.append(fn(*args, **kwargs))
        return results

    def remember(self, data):
        """Store data in agent memory."""
        self.memory.append(data)

    def recall(self, query=None):
        """Recall data from agent memory (simple search)."""
        if query is None:
            return self.memory
        return [m for m in self.memory if query in str(m)]


# Singleton agent instance
agent = Agent()
