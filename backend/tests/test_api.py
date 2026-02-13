import pytest
from fastapi.testclient import TestClient
from backend.src.main import app
from backend.src.plugin_loader import load_all_plugins, get_loaded_plugins
from backend.src.session_manager import session_manager
from backend.src.providers import provider_registry
from backend.src.permissions import permission_manager
from backend.src.learning import memory_manager

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_start_chat():
    response = client.get("/api/chat/start")
    assert response.status_code == 200
    assert "session_id" in response.json()

def test_provider_list():
    response = client.get("/api/provider/list")
    assert response.status_code == 200
    assert "providers" in response.json()

def test_plugin_loading():
    """Test that plugins are loaded from the plugins directory."""
    plugins = load_all_plugins()
    assert isinstance(plugins, list)
    # Sample plugin should be loaded
    assert any(p['manifest']['name'] == 'sample_plugin' for p in plugins)

def test_list_plugins_endpoint():
    """Test the /api/plugins endpoint."""
    response = client.get("/api/plugins")
    assert response.status_code == 200
    data = response.json()
    assert "plugins" in data
    # Verify sample plugin is in the list
    plugin_names = [p['name'] for p in data['plugins']]
    assert 'sample_plugin' in plugin_names

def test_plugin_registration():
    """Test that plugins register tools with the agent."""
    response = client.get("/api/agent/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    # Sample plugin should have registered the sample_reverse tool
    assert 'sample_reverse' in data['tools']

def test_plugin_memory_registration():
    """Test that plugins can register to agent memory."""
    response = client.get("/api/agent/memory")
    assert response.status_code == 200
    data = response.json()
    assert "memory" in data
    # Sample plugin should have added an entry to memory
    memory_items = data['memory']
    assert any(isinstance(item, dict) and item.get('plugin') == 'sample_plugin' for item in memory_items)

def test_session_creation():
    """Test that chat sessions are created properly."""
    response = client.get("/api/chat/start")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    session_id = data["session_id"]
    
    # Verify the session exists in session_manager
    session = session_manager.get_session(session_id)
    assert session is not None

def test_session_history_endpoint():
    """Test the /api/chat/{session_id}/history endpoint."""
    # Create a session
    response = client.get("/api/chat/start")
    session_id = response.json()["session_id"]
    
    # Get history (should be empty initially)
    response = client.get(f"/api/chat/{session_id}/history")
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert "actions" in data
    assert data["history"] == []
    assert data["actions"] == []

def test_session_action_logging():
    """Test that actions are logged in sessions."""
    # Create a session
    response = client.get("/api/chat/start")
    session_id = response.json()["session_id"]
    
    # Add an action through the session manager
    session_manager.add_action_to_session(session_id, "tool_call", status="completed")
    
    # Check that the action is logged
    response = client.get(f"/api/chat/{session_id}/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data["actions"]) == 1
    assert data["actions"][0]["action_type"] == "tool_call"

def test_audit_log_endpoint():
    """Test the /api/action/audit-log endpoint."""
    # Create a session and add an action
    response = client.get("/api/chat/start")
    session_id = response.json()["session_id"]
    session_manager.add_action_to_session(session_id, "test_action", status="completed")
    
    # Get audit log
    response = client.get("/api/action/audit-log")
    assert response.status_code == 200
    data = response.json()
    assert "log" in data
    assert len(data["log"]) > 0

def test_provider_registry_initialization():
    """Test that providers are registered in the provider registry."""
    providers = provider_registry.list_providers()
    assert "copilot" in providers
    assert "aws_bedrock" in providers

def test_provider_selection():
    """Test selecting an active provider."""
    response = client.post("/api/provider/select", json={"provider": "copilot"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "selected"
    assert data["provider"] == "copilot"
    
    # Verify the provider is active
    active = provider_registry.get_active_provider()
    assert active is not None
    assert active.name == "copilot"

def test_provider_config_validation():
    """Test that provider configuration is validated."""
    # Try to update config for a valid provider
    response = client.post("/api/provider/config", json={
        "provider_id": "copilot",
        "config": {"api_key": "test_key"}
    })
    assert response.status_code == 200
    assert response.json()["status"] == "updated"

def test_provider_switching():
    """Test switching between providers."""
    # Select Copilot
    response = client.post("/api/provider/select", json={"provider": "copilot"})
    assert response.status_code == 200
    
    # Verify Copilot is active
    response = client.get("/api/provider/list")
    assert response.status_code == 200
    data = response.json()
    assert data["active"] == "copilot"
    
    # Switch to Bedrock
    response = client.post("/api/provider/select", json={"provider": "aws_bedrock"})
    assert response.status_code == 200
    
    # Verify Bedrock is active
    response = client.get("/api/provider/list")
    assert response.status_code == 200
    data = response.json()
    assert data["active"] == "aws_bedrock"

def test_permission_request():
    """Test requesting permission for an action."""
    response = client.post("/api/action/request-permission", json={})
    assert response.status_code == 200
    data = response.json()
    assert "permission_id" in data
    assert "granted" in data

def test_permission_management():
    """Test permission manager functionality."""
    # Create a permission request
    permission = permission_manager.request_permission("user_123", "modify_data", "Update settings")
    assert permission is not None
    assert permission.user_id == "user_123"
    assert permission.action_type == "modify_data"
    
    # Initially should not be granted
    assert permission.required == True
    assert permission.granted == False
    
    # Grant the permission
    permission_manager.grant_permission(permission.id)
    retrieved = permission_manager.get_permission(permission.id)
    assert retrieved.granted == True

def test_auto_grant_permissions():
    """Test that safe actions are auto-granted."""
    permission = permission_manager.request_permission("user_123", "read_data", "Read settings")
    # Read actions should be auto-granted
    assert permission.granted == True

def test_memory_learning():
    """Test learning and storing memories."""
    user_id = "user_456"
    session_id = "session_789"
    
    data = {"preference": "dark_mode", "language": "en"}
    memory = memory_manager.learn(user_id, session_id, data, "preference")
    
    assert memory is not None
    assert memory.user_id == user_id
    assert memory.session_id == session_id
    assert memory.data == data

def test_memory_recall():
    """Test recalling learned memories."""
    user_id = "user_999"
    session_id = "session_000"
    
    # Learn some data
    memory_manager.learn(user_id, session_id, {"setting": "value1"}, "preference")
    memory_manager.learn(user_id, session_id, {"setting": "value2"}, "pattern")
    
    # Recall memories
    memories = memory_manager.recall(user_id)
    assert len(memories) >= 2

def test_memory_api():
    """Test memory API endpoint."""
    user_id = "api_test_user"
    
    # Learn something
    response = client.post("/api/memory/learn", json={
        "user_id": user_id,
        "session_id": "session_api",
        "data": {"test": "data"},
        "category": "general"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "learned"
    
    # Retrieve memories
    response = client.get(f"/api/memory/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert "memory" in data
    assert data["count"] >= 1

def test_permission_history():
    """Test permission history tracking."""
    # Clear any existing permissions first
    initial_count = len(permission_manager.get_permission_history())
    
    # Request a permission
    permission_manager.request_permission("user_hist", "test_action", "Test")
    
    # Get history
    history = permission_manager.get_permission_history()
    assert len(history) > initial_count

def test_audit_log_combined():
    """Test that audit log includes both action and permission logs."""
    # Add a session action
    response = client.get("/api/chat/start")
    session_id = response.json()["session_id"]
    session_manager.add_action_to_session(session_id, "audit_test", status="completed")
    
    # Request a permission
    permission_manager.request_permission("audit_user", "audit_action", "Audit test")
    
    # Get combined audit log
    response = client.get("/api/action/audit-log")
    assert response.status_code == 200
    data = response.json()
    assert len(data["log"]) > 0
