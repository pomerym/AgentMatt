from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import shlex
import logging
import re

from .agent import agent
from .plugin_loader import load_all_plugins, get_loaded_plugins, register_plugins
from .session_manager import session_manager
from .providers import provider_registry, CopilotProvider, BedrockProvider
from .permissions import permission_manager
from .command_executor import detect_command_request, execute_command_request, extract_shell_commands
from .learning import memory_manager
from .config_validator import config_validator
from .mcp_client import MCPManager, MCPError
from .bitwarden_client import BitwardenClient
from .secret_resolver import configure_bitwarden, resolve_config, resolve_secret_value

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
for noisy_logger in ("botocore", "boto3", "urllib3", "s3transfer"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)



app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../config/server.json')
PROVIDERS_PATH = os.path.join(os.path.dirname(__file__), '../config/providers.json')
BITWARDEN_PATH = os.path.join(os.path.dirname(__file__), '../config/bitwarden.json')

# AWS Bedrock model options
BEDROCK_MODELS = [
    {"id": "global.anthropic.claude-opus-4-5-20251101-v1:0", "name": "Claude Opus 4.5 (Global)"},
    {"id": "anthropic.claude-opus-4-5-20251101-v1:0", "name": "Claude Opus 4.5"},
    {"id": "anthropic.claude-3-5-sonnet-20241022-v2:0", "name": "Claude 3.5 Sonnet v2"},
    {"id": "anthropic.claude-3-5-haiku-20241022-v1:0", "name": "Claude 3.5 Haiku"},
    {"id": "anthropic.claude-3-sonnet-20240229-v1:0", "name": "Claude 3 Sonnet"},
    {"id": "anthropic.claude-3-haiku-20240307-v1:0", "name": "Claude 3 Haiku"},
    {"id": "amazon.titan-text-express-v1", "name": "Amazon Titan Text Express"},
    {"id": "amazon.titan-text-lite-v1", "name": "Amazon Titan Text Lite"},
    {"id": "amazon.titan-text-premier-v1:0", "name": "Amazon Titan Text Premier"},
    {"id": "meta.llama3-70b-instruct-v1:0", "name": "Meta Llama 3 70B Instruct"},
    {"id": "meta.llama3-8b-instruct-v1:0", "name": "Meta Llama 3 8B Instruct"},
    {"id": "mistral.mistral-large-2402-v1:0", "name": "Mistral Large"},
    {"id": "mistral.mixtral-8x7b-instruct-v0:1", "name": "Mixtral 8x7B Instruct"},
    {"id": "cohere.command-r-plus-v1:0", "name": "Cohere Command R+"},
    {"id": "cohere.command-r-v1:0", "name": "Cohere Command R"},
    {"id": "ai21.jamba-1-5-large-v1:0", "name": "AI21 Jamba 1.5 Large"},
    {"id": "ai21.jamba-1-5-mini-v1:0", "name": "AI21 Jamba 1.5 Mini"},
]

AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1",
    "ap-south-1", "ap-northeast-1", "ap-northeast-2", "ap-southeast-1", "ap-southeast-2",
    "sa-east-1", "ca-central-1"
]

def load_providers_config():
    with open(PROVIDERS_PATH) as f:
        return resolve_config(json.load(f))

def load_server_config():
    with open(CONFIG_PATH) as f:
        return resolve_config(json.load(f))

def load_bitwarden_config():
    if not os.path.exists(BITWARDEN_PATH):
        return {}
    with open(BITWARDEN_PATH) as f:
        return json.load(f)

def initialize_bitwarden():
    config = load_bitwarden_config()
    logger.info(f"[BITWARDEN] Config loaded: enabled={config.get('enabled')}, has_base_url={bool(config.get('base_url'))}")
    if not config or not config.get("enabled"):
        logger.info("[BITWARDEN] Bitwarden disabled or missing config")
        configure_bitwarden(None)
        return

    base_url = config.get("base_url")
    if not base_url:
        logger.warning("[BITWARDEN] Missing base_url in config; disabled")
        configure_bitwarden(None)
        return

    logger.info(f"[BITWARDEN] Initializing with base_url: {base_url}")
    client = BitwardenClient(
        base_url=base_url,
        cache_ttl=int(config.get("cache_ttl", 30)),
        timeout=int(config.get("timeout", 10))
    )
    aliases = config.get("aliases", {})
    logger.info(f"[BITWARDEN] Configured {len(aliases)} aliases")
    configure_bitwarden(client, aliases)
    logger.info("[BITWARDEN] Bitwarden client initialized successfully")

def save_providers_config(config):
    with open(PROVIDERS_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def save_server_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def initialize_providers():
    """Load providers from config and initialize them."""
    logger.info("[PROVIDERS] Initializing providers...")
    
    try:
        config = load_providers_config()
        provider_configs = config.get("providers", {})
        
        # Register Copilot provider
        copilot_config = provider_configs.get("copilot", {})
        copilot = CopilotProvider(config=copilot_config)
        provider_registry.register_provider(copilot)
        logger.info(f"[PROVIDERS] Registered Copilot provider")
        
        # Try to initialize it
        if copilot.validate_config():
            copilot.initialize()
            logger.info(f"[PROVIDERS] Copilot provider initialized successfully")
        else:
            logger.warning(f"[PROVIDERS] Copilot provider config invalid, not initialized")
        
        # Register AWS Bedrock provider
        bedrock_config = provider_configs.get("aws_bedrock", {})
        bedrock = BedrockProvider(config=bedrock_config)
        provider_registry.register_provider(bedrock)
        logger.info(f"[PROVIDERS] Registered AWS Bedrock provider")
        
        # Try to initialize it
        if bedrock.validate_config():
            bedrock.initialize()
            logger.info(f"[PROVIDERS] AWS Bedrock provider initialized successfully")
        else:
            logger.warning(f"[PROVIDERS] AWS Bedrock provider config invalid, not initialized")
        
        # Set active provider from config
        active = config.get("provider", "copilot")
        if provider_registry.set_active_provider(active):
            logger.info(f"[PROVIDERS] Active provider set to: {active}")
        else:
            logger.warning(f"[PROVIDERS] Could not set active provider to {active}")

        return True
        
    except Exception as e:
        logger.error(f"[PROVIDERS] Failed to initialize providers: {str(e)}")
        logger.exception("[PROVIDERS] Full traceback:")
        return False


initialize_bitwarden()

server_config = load_server_config()
mcp_manager = MCPManager(server_config.get("mcp", {}))


def _normalize_command(command: str) -> str:
    if not command:
        return ""
    parts = [p.strip() for p in re.split(r"\s*(?:&&|\|\||;)\s*", command) if p.strip()]
    if not parts:
        return command.strip()

    for part in parts:
        tokens = _command_tokens(part, normalize=False)
        if not tokens:
            continue
        if tokens[0] == "cd":
            continue
        return part

    return parts[-1]


def _command_tokens(command: str, normalize: bool = True) -> list[str]:
    if not command:
        return []
    target = _normalize_command(command) if normalize else command
    try:
        return shlex.split(target)
    except ValueError:
        return target.strip().split()


def _command_key(command: str) -> str:
    tokens = _command_tokens(command)
    return tokens[0] if tokens else ""


def _command_subkey(command: str) -> str:
    tokens = _command_tokens(command)
    return " ".join(tokens[:2]) if len(tokens) >= 2 else (tokens[0] if tokens else "")


def _command_matches_scope(command: str, scope: dict) -> bool:
    if not scope:
        return False
    mode = (scope.get("mode") or "").lower()
    pattern = (scope.get("pattern") or "").strip()
    command = _normalize_command(command)
    if mode == "all":
        return True
    if mode == "command":
        return _command_key(command) == pattern
    if mode in ("command_subcommand", "command-subcommand"):
        return _command_subkey(command) == pattern
    if mode == "exact":
        return command.strip() == pattern
    return False


def _set_command_scope_from_pending(session, pending: dict, raw_args: str) -> dict:
    if not pending or pending.get("type") != "shell":
        return {}
    command = _normalize_command(pending.get("command", "").strip())
    args = (raw_args or "").strip().lower()
    if not args:
        return {}

    if args in ("all", "*"):
        return {"mode": "all", "pattern": "*"}

    if args.startswith("command"):
        parts = args.split(":", 1)
        if len(parts) > 1 and parts[1].strip():
            return {"mode": "command", "pattern": parts[1].strip()}
        return {"mode": "command", "pattern": _command_key(command)}

    if args.startswith("command-subcommand") or args.startswith("command_subcommand"):
        parts = args.split(":", 1)
        if len(parts) > 1 and parts[1].strip():
            return {"mode": "command_subcommand", "pattern": parts[1].strip()}
        return {"mode": "command_subcommand", "pattern": _command_subkey(command)}

    if args.startswith("exact"):
        parts = args.split(":", 1)
        if len(parts) > 1 and parts[1].strip():
            return {"mode": "exact", "pattern": parts[1].strip()}
        return {"mode": "exact", "pattern": command}

    return {}


def _get_persistent_scopes(user_id: str) -> list[dict]:
    try:
        return memory_manager.get_approval_scopes(user_id)
    except Exception:
        return []


def _scope_allows_command(session, command: str) -> bool:
    if not command:
        return False
    scopes = []
    session_scope = session.settings.get("command_approval_scope")
    if session_scope:
        scopes.append(session_scope)
    scopes.extend(_get_persistent_scopes(session.user_id))
    return any(_command_matches_scope(command, scope) for scope in scopes)


def _format_mcp_tools(tools: list[dict]) -> str:
    if not tools:
        return "No MCP tools found."
    lines = ["Available MCP tools:"]
    for tool in tools:
        name = tool.get("name", "")
        server_id = tool.get("server_id", "")
        description = tool.get("description", "")
        entry = f"- {server_id}/{name}"
        if description:
            entry += f": {description}"
        lines.append(entry)
    return "\n".join(lines)


def _handle_mcp_command(message_content: str) -> str:
    parts = shlex.split(message_content)
    if len(parts) == 1 or parts[1] in {"help", "?"}:
        return (
            "MCP usage:\n"
            "/mcp servers\n"
            "/mcp list\n"
            "/mcp <server_id> <tool_name> {json_args}"
        )

    subcommand = parts[1].lower()
    if subcommand == "servers":
        servers = mcp_manager.list_servers()
        if not servers:
            return "No MCP servers configured."
        lines = ["Configured MCP servers:"]
        for server in servers:
            name = server.get("name") or server.get("id")
            transport = server.get("transport")
            lines.append(f"- {server.get('id')}: {name} ({transport})")
        return "\n".join(lines)

    if subcommand == "list":
        return _format_mcp_tools(mcp_manager.list_tools())

    if len(parts) < 3:
        return "Usage: /mcp <server_id> <tool_name> {json_args}"

    server_id = parts[1]
    tool_name = parts[2]
    args_raw = " ".join(parts[3:]).strip()
    arguments = {}
    if args_raw:
        try:
            arguments = json.loads(args_raw)
        except json.JSONDecodeError:
            return "Invalid JSON args. Example: /mcp server tool {\"query\": \"value\"}"

    try:
        result = mcp_manager.call_tool(server_id, tool_name, arguments)
    except MCPError as exc:
        return f"MCP error: {exc}"
    except Exception as exc:
        return f"MCP error: {exc}"

    return json.dumps(result, indent=2)


def _extract_mcp_commands(text: str) -> list:
    """Extract MCP commands from text"""
    commands = []
    for line in text.splitlines():
        if "/mcp" not in line:
            continue
        try:
            tokens = shlex.split(line)
        except ValueError:
            continue
        for idx, token in enumerate(tokens):
            if token != "/mcp":
                continue
            if idx + 1 >= len(tokens):
                continue
            first = tokens[idx + 1]
            if first in {"list", "servers", "help", "?"}:
                continue

            server_id = ""
            tool_name = ""
            args_tokens = []

            if "/" in first and (idx + 2 >= len(tokens) or tokens[idx + 2].startswith("{")):
                server_id, tool_name = first.split("/", 1)
                args_tokens = tokens[idx + 2:]
            elif idx + 2 < len(tokens):
                server_id = first
                tool_name = tokens[idx + 2]
                args_tokens = tokens[idx + 3:]
            else:
                continue

            args_raw = " ".join(args_tokens).strip()
            arguments = {}
            if args_raw:
                try:
                    arguments = json.loads(args_raw)
                except json.JSONDecodeError:
                    arguments = {}

            if server_id and tool_name:
                commands.append({"server_id": server_id, "tool_name": tool_name, "arguments": arguments})
    return commands


def _execute_mcp_commands_in_response(ai_response: str) -> tuple[str, list]:
    """Execute any MCP commands found in AI response and return updated response with results"""
    mcp_commands = _extract_mcp_commands(ai_response)
    if not mcp_commands:
        return ai_response, []
    
    results = []
    for cmd in mcp_commands:
        try:
            result = mcp_manager.call_tool(cmd["server_id"], cmd["tool_name"], cmd["arguments"])
            results.append({"command": cmd, "result": result, "success": True})
        except Exception as exc:
            results.append({"command": cmd, "error": str(exc), "success": False})
    
    return ai_response, results


def _send_to_provider(session_id: str, session, message_content: str) -> dict:
    config = load_providers_config()
    active_provider = config.get("provider", "copilot")
    logger.info(f"[CHAT MESSAGE] Active provider: {active_provider}")

    provider = provider_registry.get_provider(active_provider)
    if not provider:
        error_msg = f"Provider '{active_provider}' not found"
        logger.error(f"[CHAT MESSAGE] {error_msg}")
        return {"error": error_msg}, 500

    logger.info(f"[CHAT MESSAGE] Found provider: {provider.name}")

    if not provider.initialized:
        logger.warning(f"[CHAT MESSAGE] Provider {provider.name} not initialized, attempting initialization...")

        if not provider.validate_config():
            error_msg = f"Provider '{active_provider}' is not properly configured. Please configure it in settings."
            logger.error(f"[CHAT MESSAGE] {error_msg}")
            session_manager.add_message_to_session(session_id, "assistant", error_msg)
            return {"error": error_msg}, 500

        if not provider.initialize():
            error_msg = f"Failed to initialize provider '{active_provider}'. Check your configuration."
            logger.error(f"[CHAT MESSAGE] {error_msg}")
            session_manager.add_message_to_session(session_id, "assistant", error_msg)
            return {"error": error_msg}, 500

        logger.info(f"[CHAT MESSAGE] Provider {provider.name} initialized successfully")

    session_history = session_manager.get_session_history(session_id)
    history_for_provider = []
    system_parts = [
        "You are AgentMatt. Maintain continuity across turns and use provided memory if relevant.",
        "Be concise, but include reasoning steps when the user asks for analysis or decisions.",
        "If unsure, ask a clarifying question rather than guessing."
    ]

    if session.settings.get("verbose"):
        system_parts.append(
            "Verbose mode is enabled. Provide a brief 'Reasoning Summary' with high-level steps only."
        )

    profile = memory_manager.get_profile(session.user_id)
    if profile:
        system_parts.append("User profile:\n" + json.dumps(profile, indent=2))

    latest_summary = memory_manager.get_latest_summary(session.user_id)
    if latest_summary and isinstance(latest_summary.data, dict):
        summary_text = latest_summary.data.get("summary")
        if summary_text:
            system_parts.append("Recent session summary:\n" + summary_text)

    memory_hits = memory_manager.search(session.user_id, message_content, limit=5)
    if memory_hits:
        memory_lines = []
        for mem in memory_hits:
            data = mem.data
            if isinstance(data, dict):
                data = json.dumps(data)
            memory_lines.append(f"- {data}")
        system_parts.append("Relevant long-term memory:\n" + "\n".join(memory_lines))

    for msg in session_history[-20:]:
        role = "assistant" if msg.get("sender") == "assistant" else "user"
        content = msg.get("content", "")
        if content:
            # Resolve any Bitwarden credential references in history
            logger.debug(f"[CHAT MESSAGE] Processing history message, original length: {len(content)}")
            resolved_content = resolve_secret_value(content)
            logger.debug(f"[CHAT MESSAGE] Resolved history, new length: {len(resolved_content)}, changed={content != resolved_content}")
            history_for_provider.append({"role": role, "content": resolved_content})

    try:
        # Resolve any Bitwarden credential references in the current message
        logger.info(f"[CHAT MESSAGE] Current message (original): {message_content[:100] if len(message_content) > 100 else message_content}")
        resolved_message = resolve_secret_value(message_content)
        logger.info(f"[CHAT MESSAGE] Current message (resolved): {resolved_message[:100] if len(resolved_message) > 100 else resolved_message}")
        logger.info(f"[CHAT MESSAGE] Message changed: {message_content != resolved_message}")
        logger.info(f"[CHAT MESSAGE] Sending message to {provider.name} provider")
        ai_response = provider.send_message(
            resolved_message,
            {
                "session_id": session_id,
                "history": history_for_provider,
                "system": "\n\n".join(system_parts)
            }
        )
        logger.info(f"[CHAT MESSAGE] Received response from {provider.name}: {ai_response[:100] if ai_response else 'None'}")

        if ai_response and ai_response.startswith("Error:"):
            logger.error(f"[CHAT MESSAGE] Provider returned error: {ai_response}")
            session_manager.add_message_to_session(session_id, "assistant", ai_response)
            return {"error": ai_response}, 500

        # Check for MCP commands in the AI response and execute them
        updated_response,mcp_results = _execute_mcp_commands_in_response(ai_response or "")
        if mcp_results:
            logger.info(f"[CHAT MESSAGE] Executed {len(mcp_results)} MCP command(s) from AI response")
            # Build a response that includes the MCP results
            result_parts = []
            for mcp_result in mcp_results:
                if mcp_result["success"]:
                    cmd = mcp_result["command"]
                    result = mcp_result["result"]
                    # Format the result for the AI
                    result_text = json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
                    result_parts.append(f"Result from {cmd['tool_name']}:\n{result_text}")
                else:
                    cmd = mcp_result["command"]
                    result_parts.append(f"Error from {cmd['tool_name']}: {mcp_result.get('error', 'Unknown error')}")
            
            # Add the results to the conversation and ask the AI to summarize
            combined_results = "\n\n".join(result_parts)
            session_manager.add_message_to_session(session_id, "assistant", updated_response)
            session_manager.add_message_to_session(session_id, "system", f"MCP Tool Results:\n{combined_results}")
            
            # Ask the AI to provide a user-friendly response based on the results
            history_with_results = history_for_provider + [
                {"role": "assistant", "content": updated_response},
                {"role": "user", "content": f"Based on these MCP tool results, please provide a clear summary:\n\n{combined_results}"}
            ]
            
            try:
                final_response = provider.send_message(
                    "Summarize the above MCP results for the user",
                    {
                        "session_id": session_id,
                        "history": history_with_results,
                        "system": "\n\n".join(system_parts)
                    }
                )
                ai_response = final_response
            except Exception as e:
                logger.error(f"[CHAT MESSAGE] Error getting final response after MCP: {e}")
                ai_response = f"{updated_response}\n\n{combined_results}"

        suggested_commands = extract_shell_commands(ai_response or "")
        if suggested_commands:
            pending_queue = session.settings.get("pending_commands") or []
            for cmd in suggested_commands:
                pending_queue.append({"type": "shell", "command": cmd, "action_type": "command"})

            while pending_queue and _scope_allows_command(session, pending_queue[0].get("command", "")):
                next_cmd = pending_queue.pop(0)
                session_manager.add_action_to_session(
                    session_id,
                    next_cmd.get("action_type", "command"),
                    status="completed",
                    permission_requested=False,
                    permission_granted=True
                )
                response_text = execute_command_request(next_cmd)
                session_manager.add_message_to_session(
                    session_id,
                    "assistant",
                    response_text,
                    action_taken=next_cmd.get("action_type", "command")
                )

            if pending_queue:
                next_cmd = pending_queue[0]
                if not next_cmd.get("permission_id"):
                    permission = permission_manager.request_permission(
                        "default",
                        "command",
                        f"Run command: {_normalize_command(next_cmd.get('command', ''))}",
                        required=True
                    )
                    next_cmd["permission_id"] = permission.id
                    pending_queue[0] = next_cmd

                session.settings["pending_commands"] = pending_queue
                session_manager._save()
                session_manager.add_action_to_session(
                    session_id,
                    "command",
                    status="pending",
                    permission_requested=True,
                    permission_granted=False
                )
                session_manager.add_message_to_session(session_id, "assistant", ai_response)
                session_manager.add_message_to_session(
                    session_id,
                    "assistant",
                    "Approval required to run: "
                    f"{_normalize_command(next_cmd.get('command', ''))}\n"
                    "Reply with /approve, /approve command (permanent), /approve command-subcommand (permanent), /approve exact, or /deny.",
                    action_taken="command"
                )
                session_history = session_manager.get_session_history(session_id)
                return {
                    "session_id": session_id,
                    "status": "ok",
                    "message": "Approval required",
                    "messages_count": len(session_history)
                }

        session_manager.add_message_to_session(session_id, "assistant", ai_response)
        logger.info(f"[CHAT MESSAGE] AI response added to session")
        session_history = session_manager.get_session_history(session_id)
        logger.info(f"[CHAT MESSAGE] Message processed successfully. Total messages: {len(session_history)}")
        return {
            "session_id": session_id,
            "status": "ok",
            "message": "Message processed",
            "messages_count": len(session_history)
        }
    except Exception as e:
        error_msg = f"Error calling AI provider: {str(e)}"
        logger.error(f"[CHAT MESSAGE] {error_msg}")
        logger.exception("[CHAT MESSAGE] Full exception:")
        return {"error": error_msg}, 500

# Load and register plugins on startup
load_all_plugins()
register_plugins(agent)

# Initialize providers after plugins and agent are ready
initialize_providers()

@app.post("/api/chat/start")
async def start_chat(request: Request = None):
    """Start a new chat session."""
    logger.info(f"[CHAT START] Creating new session")
    name = None
    if request is not None:
        try:
            payload = await request.json()
            name = (payload or {}).get("name")
        except Exception:
            name = None
    session = session_manager.create_session(name=name)
    logger.info(f"[CHAT START] Session created: {session.session_id}")
    return {"session_id": session.session_id, "name": session.name, "status": "started"}

@app.get("/api/chat/start")
def start_chat_get():
    """Start a new chat session (legacy GET)."""
    logger.info(f"[CHAT START] Creating new session (GET)")
    session = session_manager.create_session()
    logger.info(f"[CHAT START] Session created: {session.session_id}")
    return {"session_id": session.session_id, "name": session.name, "status": "started"}

@app.post("/api/chat/{session_id}/close")
def close_chat(session_id: str):
    """Close an existing chat session."""
    logger.info(f"[CHAT CLOSE] Closing session: {session_id}")
    session = session_manager.get_session(session_id)
    if not session:
        logger.error(f"[CHAT CLOSE] Session not found: {session_id}")
        return {"error": "Session not found"}, 404
    session_manager.close_session(session_id)
    return {"status": "closed", "session_id": session_id}

@app.get("/api/chat/sessions")
def list_chat_sessions():
    """List existing chat sessions."""
    sessions = session_manager.list_sessions()
    return {"sessions": sessions}

@app.post("/api/chat/{session_id}/rename")
async def rename_chat_session(session_id: str, request: Request):
    """Rename an existing chat session."""
    try:
        payload = await request.json()
    except Exception as e:
        return {"error": f"Invalid request body: {str(e)}"}, 400

    name = (payload or {}).get("name")
    if not name or not str(name).strip():
        return {"error": "Session name cannot be empty"}, 400

    session = session_manager.rename_session(session_id, str(name).strip())
    if not session:
        return {"error": "Session not found"}, 404

    return {"status": "renamed", "session_id": session.session_id, "name": session.name}

@app.get("/api/chat/{session_id}/history")
def get_history(session_id: str):
    """Get chat history and action log for a session."""
    logger.info(f"[CHAT HISTORY] Fetching history for session: {session_id}")
    
    session = session_manager.get_session(session_id)
    if not session:
        logger.error(f"[CHAT HISTORY] Session not found: {session_id}")
        return {"error": "Session not found"}, 404
    
    history = session_manager.get_session_history(session_id)
    actions = session_manager.get_session_actions(session_id)
    
    logger.info(f"[CHAT HISTORY] Session {session_id}: {len(history)} messages, {len(actions)} actions")
    logger.debug(f"[CHAT HISTORY] History: {history}")
    
    return {"session_id": session_id, "history": history, "actions": actions}

@app.post("/api/chat/{session_id}/message")
async def post_message(session_id: str, request: Request):
    """Post a message to a chat session."""
    try:
        logger.info(f"[CHAT MESSAGE] Received message for session: {session_id}")
        
        # Read request body
        try:
            body = await request.json()
            message_content = body.get("message", "").strip()
            logger.info(f"[CHAT MESSAGE] Message content: {message_content[:100]}")
        except Exception as e:
            error_msg = f"Invalid request body: {str(e)}"
            logger.error(f"[CHAT MESSAGE] {error_msg}")
            return {"error": error_msg}, 400
        
        if not message_content:
            error_msg = "Message cannot be empty"
            logger.error(f"[CHAT MESSAGE] {error_msg}")
            return {"error": error_msg}, 400
        
        # Get the session
        session = session_manager.get_session(session_id)
        if not session:
            error_msg = f"Session '{session_id}' not found"
            logger.error(f"[CHAT MESSAGE] {error_msg}")
            return {"error": error_msg}, 404
        
        logger.info(f"[CHAT MESSAGE] Found session, adding user message")

        if message_content.startswith("/verbose"):
            parts = message_content.split()
            mode = parts[1].lower() if len(parts) > 1 else "on"
            enabled = mode in ["on", "true", "1", "yes"]
            session.settings["verbose"] = enabled
            session_manager._save()
            session_manager.add_message_to_session(session_id, "user", message_content)
            reply = f"Verbose mode {'enabled' if enabled else 'disabled'} for this session."
            session_manager.add_message_to_session(session_id, "assistant", reply)
            session_history = session_manager.get_session_history(session_id)
            return {
                "session_id": session_id,
                "status": "ok",
                "message": "Verbose updated",
                "messages_count": len(session_history)
            }

        if message_content.startswith("/autocontinue"):
            parts = message_content.split()
            mode = parts[1].lower() if len(parts) > 1 else "on"
            enabled = mode in ["on", "true", "1", "yes"]
            session.settings["auto_continue"] = enabled
            session_manager._save()
            session_manager.add_message_to_session(session_id, "user", message_content)
            reply = f"Auto-continue {'enabled' if enabled else 'disabled'} for this session."
            session_manager.add_message_to_session(session_id, "assistant", reply)
            session_history = session_manager.get_session_history(session_id)
            return {
                "session_id": session_id,
                "status": "ok",
                "message": "Auto-continue updated",
                "messages_count": len(session_history)
            }

        if message_content.startswith("/mcp"):
            session_manager.add_message_to_session(session_id, "user", message_content)
            reply = _handle_mcp_command(message_content)
            session_manager.add_message_to_session(session_id, "assistant", reply)
            session_history = session_manager.get_session_history(session_id)
            return {
                "session_id": session_id,
                "status": "ok",
                "message": "MCP handled",
                "messages_count": len(session_history)
            }

        if message_content.startswith("/approve") or message_content.startswith("/deny"):
            approved = message_content.startswith("/approve")
            session_manager.add_message_to_session(session_id, "user", message_content)
            pending_queue = session.settings.get("pending_commands")
            if not pending_queue and session.settings.get("pending_command"):
                pending_queue = [session.settings.get("pending_command")]

            if not pending_queue:
                reply = "No pending command to approve or deny."
                session_manager.add_message_to_session(session_id, "assistant", reply)
                session_history = session_manager.get_session_history(session_id)
                return {
                    "session_id": session_id,
                    "status": "ok",
                    "message": "No pending command",
                    "messages_count": len(session_history)
                }

            pending = pending_queue.pop(0)
            approve_args = message_content[len("/approve"):].strip() if approved else ""
            permission_id = pending.get("permission_id")
            action_type = pending.get("action_type", "command")
            command_scope = session.settings.get("command_approval_scope")
            if approved:
                if permission_id:
                    permission_manager.grant_permission(permission_id)
                new_scope = _set_command_scope_from_pending(session, pending, approve_args)
                if new_scope:
                    command_scope = new_scope
                    session.settings["command_approval_scope"] = new_scope
                session_manager.add_action_to_session(
                    session_id,
                    action_type,
                    status="completed",
                    permission_requested=True,
                    permission_granted=True
                )
                response_text = execute_command_request(pending)
                session_manager.add_message_to_session(session_id, "assistant", response_text, action_taken=action_type)
            else:
                if permission_id:
                    permission_manager.deny_permission(permission_id)
                session_manager.add_action_to_session(
                    session_id,
                    action_type,
                    status="denied",
                    permission_requested=True,
                    permission_granted=False
                )
                session_manager.add_message_to_session(session_id, "assistant", "Command denied.", action_taken=action_type)

            while pending_queue and approved and _scope_allows_command(session, pending_queue[0].get("command", "")):
                next_cmd = pending_queue.pop(0)
                session_manager.add_action_to_session(
                    session_id,
                    next_cmd.get("action_type", "command"),
                    status="completed",
                    permission_requested=False,
                    permission_granted=True
                )
                response_text = execute_command_request(next_cmd)
                session_manager.add_message_to_session(
                    session_id,
                    "assistant",
                    response_text,
                    action_taken=next_cmd.get("action_type", "command")
                )

            if pending_queue:
                next_cmd = pending_queue[0]
                next_permission = permission_manager.request_permission(
                    "default",
                    next_cmd.get("action_type", "command"),
                    f"Run command: {_normalize_command(next_cmd.get('command', ''))}",
                    required=True
                )
                next_cmd["permission_id"] = next_permission.id
                pending_queue[0] = next_cmd
                session.settings["pending_commands"] = pending_queue
                session_manager._save()
                session_manager.add_message_to_session(
                    session_id,
                    "assistant",
                    "Approval required to run: "
                    f"{_normalize_command(next_cmd.get('command', ''))}\n"
                    "Reply with /approve, /approve command (permanent), /approve command-subcommand (permanent), /approve exact, or /deny.",
                    action_taken="command"
                )
            else:
                session.settings.pop("pending_commands", None)
                session.settings.pop("pending_command", None)
                session_manager._save()

            followup = session.settings.pop("pending_followup", None) if approved else None
            if approved and followup:
                session_manager._save()
                session_manager.add_message_to_session(session_id, "user", "continue")
                return _send_to_provider(session_id, session, "continue")

            session_history = session_manager.get_session_history(session_id)
            return {
                "session_id": session_id,
                "status": "ok",
                "message": "Command processed",
                "messages_count": len(session_history)
            }
        
        # Add user message to session
        session_manager.add_message_to_session(session_id, "user", message_content)
        memory_manager.maybe_learn_from_message(session.user_id, session_id, message_content)
        session_history = session_manager.get_session_history(session_id)
        memory_manager.maybe_summarize_session(session.user_id, session_id, session_history)
        logger.info(f"[CHAT MESSAGE] User message added to session")
        
        # Check for command requests before calling the AI provider
        command_request = detect_command_request(message_content)
        if command_request:
            logger.info(f"[CHAT MESSAGE] Detected command request: {command_request}")
            action_type = "command"
            description = "Requested command"
            if command_request.get("type") == "inspect_path":
                action_type = "inspect_path"
                description = f"Inspect path: {command_request.get('path')}"
            elif command_request.get("type") == "shell":
                description = f"Run command: {command_request.get('command')}"

            permission = permission_manager.request_permission(
                "default",
                action_type,
                description,
                required=True
            )

            command_request["permission_id"] = permission.id
            command_request["action_type"] = action_type
            session.settings["pending_commands"] = [command_request]
            if session.settings.get("auto_continue", True):
                session.settings["pending_followup"] = {"mode": "auto_continue"}
            session_manager._save()

            prompt = (
                "Approval required to run the requested command. "
                "Reply with /approve, /approve command (permanent), /approve command-subcommand (permanent), /approve exact, or /deny."
            )
            session_manager.add_message_to_session(session_id, "assistant", prompt, action_taken=action_type)
            session_history = session_manager.get_session_history(session_id)
            return {
                "session_id": session_id,
                "status": "ok",
                "message": "Approval required",
                "messages_count": len(session_history)
            }

        return _send_to_provider(session_id, session, message_content)
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(f"[CHAT MESSAGE] {error_msg}")
        return {"error": error_msg}, 500


@app.get("/api/provider/list")
def provider_list():
    """List all available AI providers."""
    config = load_providers_config()
    available = []
    
    # Get registered providers from provider_registry
    for name in provider_registry.list_providers():
        available.append({
            "id": name,
            "enabled": config.get("providers", {}).get(name, {}).get("enabled", False),
            "name": "AWS Bedrock" if name == "aws_bedrock" else "Copilot" if name == "copilot" else name.title()
        })
    
    return {"providers": available, "active": config.get("provider")}

@app.post("/api/provider/select")
async def provider_select(request: Request):
    """Select the active AI provider."""
    body = await request.json()
    provider_id = body.get("provider")
    
    # Set active provider in registry
    if not provider_registry.set_active_provider(provider_id):
        return {"status": "error", "message": f"Provider '{provider_id}' not found"}
    
    # Save to config
    config = load_providers_config()
    config["provider"] = provider_id
    save_providers_config(config)
    
    return {"status": "selected", "provider": provider_id}

@app.get("/api/provider/config")
def provider_config():
    """Get current provider configuration."""
    config = load_providers_config()
    return config

@app.post("/api/provider/config")
async def update_provider_config(request: Request):
    """Update configuration for an AI provider."""
    try:
        body = await request.json()
        logger.info(f"[PROVIDER CONFIG] Update request received: {json.dumps(body, indent=2)}")
        
        config = load_providers_config()
        
        provider_id = body.get("provider_id")
        provider_new_config = body.get("config", {})
        
        logger.info(f"[PROVIDER CONFIG] Provider ID: {provider_id}")
        logger.debug(f"[PROVIDER CONFIG] New config: {json.dumps(provider_new_config, indent=2)}")
        
        # Get the provider from registry
        provider = provider_registry.get_provider(provider_id)
        if not provider:
            error_msg = f"Provider '{provider_id}' not found in registry"
            logger.error(f"[PROVIDER CONFIG] {error_msg}")
            return {"status": "error", "message": error_msg}
        
        logger.info(f"[PROVIDER CONFIG] Found provider: {provider.name}")
        
        # Update provider configuration
        provider.config.update(provider_new_config)
        logger.debug(f"[PROVIDER CONFIG] Updated provider config: {json.dumps(provider.config, indent=2)}")
        
        # Validate configuration
        is_valid = provider.validate_config()
        logger.info(f"[PROVIDER CONFIG] Validation result: {is_valid}")
        
        if not is_valid:
            if provider_id == "aws_bedrock":
                required_fields = ["access_key_id", "secret_access_key", "region", "model_id"]
                missing = [f for f in required_fields if not provider.config.get(f)]
                error_msg = f"Invalid AWS Bedrock configuration. Missing or empty fields: {missing}"
            else:
                error_msg = f"Invalid configuration for provider '{provider_id}'"
            logger.error(f"[PROVIDER CONFIG] Validation failed: {error_msg}")
            return {"status": "error", "message": error_msg}
        
        # Save to config file
        logger.info(f"[PROVIDER CONFIG] Saving configuration to file")
        if provider_id not in config.get("providers", {}):
            if "providers" not in config:
                config["providers"] = {}
            config["providers"][provider_id] = {}
        
        config["providers"][provider_id].update(provider_new_config)
        save_providers_config(config)
        logger.info(f"[PROVIDER CONFIG] Configuration saved successfully for provider: {provider_id}")
        
        # Re-initialize the provider with the new configuration
        logger.info(f"[PROVIDER CONFIG] Re-initializing provider with new configuration")
        provider.config = provider_new_config
        
        # Try to initialize
        if provider.validate_config():
            if provider.initialize():
                logger.info(f"[PROVIDER CONFIG] Provider {provider_id} re-initialized successfully")
            else:
                logger.warning(f"[PROVIDER CONFIG] Provider {provider_id} failed to initialize despite valid config")
        else:
            logger.warning(f"[PROVIDER CONFIG] Provider {provider_id} configuration is invalid")
        
        return {"status": "updated", "provider": provider_id}
    
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in request body: {str(e)}"
        logger.error(f"[PROVIDER CONFIG] {error_msg}")
        return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(f"[PROVIDER CONFIG] {error_msg}")
        return {"status": "error", "message": error_msg}

@app.get("/api/provider/bedrock/models")
def get_bedrock_models():
    return {"models": BEDROCK_MODELS}

@app.get("/api/provider/bedrock/regions")
def get_bedrock_regions():
    return {"regions": AWS_REGIONS}

@app.post("/api/provider/bedrock/test")
async def test_bedrock_connection(request: Request):
    """Test AWS Bedrock connection with provided credentials"""
    body = await request.json()
    # In a real implementation, this would test the connection
    # For now, return a mock response
    return {"status": "success", "message": "Connection test placeholder"}

@app.post("/api/action/request-permission")
def request_permission(request: Request):
    """Request permission for an action."""
    # In a real implementation, this would be async
    body = {"action_type": "default", "action_description": "default action"}  # Default for simple testing
    
    user_id = body.get("user_id", "default")
    action_type = body.get("action_type", "default")
    action_description = body.get("action_description", action_type)
    required = body.get("required", True)
    
    permission = permission_manager.request_permission(user_id, action_type, action_description, required)
    return {"permission_id": permission.id, "granted": permission.granted}

@app.get("/api/action/audit-log")
def audit_log():
    """Get all action logs from all sessions and permission history."""
    session_actions = session_manager.get_all_actions()
    permission_history = permission_manager.get_permission_history()
    
    # Combine both logs
    combined_log = session_actions + permission_history
    # Sort by timestamp
    combined_log.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {"log": combined_log}


@app.get("/api/memory/{user_id}")
def get_memory(user_id: str):
    """Get all learned memories for a user."""
    memories = memory_manager.get_all_user_memories(user_id)
    return {
        "user_id": user_id,
        "memory": [m.to_dict() for m in memories],
        "count": len(memories)
    }

@app.post("/api/memory/learn")
async def learn_memory(request: Request):
    """Learn and store new information."""
    body = await request.json()
    
    user_id = body.get("user_id", "default")
    session_id = body.get("session_id", "default")
    data = body.get("data", {})
    category = body.get("category", "general")
    
    memory = memory_manager.learn(user_id, session_id, data, category)
    return {
        "status": "learned",
        "memory_id": memory.id,
        "user_id": user_id
    }

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/plugins")
def list_plugins():
    plugins = get_loaded_plugins()
    return {"plugins": [p['manifest'] for p in plugins]}

@app.get("/api/agent/tools")
def list_tools():
    mcp_tools = []
    try:
        mcp_tools = [f"mcp:{t['server_id']}/{t['name']}" for t in mcp_manager.list_tools()]
    except Exception as exc:
        logger.warning("[MCP] Failed to list tools: %s", exc)
    tools = list(agent.tools.keys()) + mcp_tools
    return {"tools": tools}

@app.get("/api/mcp/servers")
def list_mcp_servers():
    return {"servers": mcp_manager.list_servers()}

@app.get("/api/mcp/tools")
def list_mcp_tools():
    return {"tools": mcp_manager.list_tools()}

@app.post("/api/mcp/call")
async def call_mcp_tool(request: Request):
    body = await request.json()
    server_id = body.get("server_id")
    tool_name = body.get("tool_name")
    arguments = body.get("arguments") or {}

    if not server_id or not tool_name:
        return {"error": "server_id and tool_name are required"}, 400

    try:
        result = mcp_manager.call_tool(server_id, tool_name, arguments)
        return {"result": result}
    except MCPError as exc:
        return {"error": str(exc)}, 400
    except Exception as exc:
        return {"error": str(exc)}, 500

@app.post("/api/mcp/server")
async def save_mcp_server(request: Request):
    """Add or update MCP server configuration."""
    body = await request.json()
    server_id = body.get("id")
    if not server_id:
        return {"error": "Server id is required"}, 400

    server_config = {
        "id": server_id,
        "name": body.get("name"),
        "transport": body.get("transport")
    }

    if server_config["transport"] == "http":
        server_config["url"] = body.get("url")
        if body.get("headers"):
            server_config["headers"] = body.get("headers")
    elif server_config["transport"] == "stdio":
        server_config["command"] = body.get("command")
        if body.get("args"):
            server_config["args"] = body.get("args")
        if body.get("cwd"):
            server_config["cwd"] = body.get("cwd")
        if body.get("env"):
            server_config["env"] = body.get("env")
    else:
        return {"error": "Invalid transport"}, 400

    try:
        config = load_server_config()
        if "mcp" not in config:
            config["mcp"] = {"tool_cache_ttl": 30, "servers": []}
        
        servers = config["mcp"].get("servers", [])
        existing_idx = next((i for i, s in enumerate(servers) if s.get("id") == server_id), None)
        
        if existing_idx is not None:
            servers[existing_idx] = server_config
        else:
            servers.append(server_config)
        
        config["mcp"]["servers"] = servers
        save_server_config(config)
        
        # Reinitialize MCP manager
        global mcp_manager
        mcp_manager = MCPManager(config.get("mcp", {}))
        
        return {"status": "saved", "server_id": server_id}
    except Exception as exc:
        logger.exception("[MCP] Failed to save server config")
        return {"error": str(exc)}, 500

@app.delete("/api/mcp/server/{server_id}")
async def delete_mcp_server(server_id: str):
    """Delete MCP server configuration."""
    try:
        config = load_server_config()
        if "mcp" not in config or "servers" not in config["mcp"]:
            return {"error": "No MCP servers configured"}, 404
        
        servers = config["mcp"]["servers"]
        filtered = [s for s in servers if s.get("id") != server_id]
        
        if len(filtered) == len(servers):
            return {"error": f"Server {server_id} not found"}, 404
        
        config["mcp"]["servers"] = filtered
        save_server_config(config)
        
        # Reinitialize MCP manager
        global mcp_manager
        mcp_manager = MCPManager(config.get("mcp", {}))
        
        return {"status": "deleted", "server_id": server_id}
    except Exception as exc:
        logger.exception("[MCP] Failed to delete server")
        return {"error": str(exc)}, 500

@app.get("/api/agent/memory")
def get_agent_memory():
    return {"memory": agent.recall()}
@app.post("/api/config/validate")
async def validate_config(request: Request):
    """Validate configuration against schema."""
    body = await request.json()
    config_file = body.get("config_file")  # "server", "providers", "bitwarden"
    schema_map = {
        "server": "server.schema.json",
        "providers": "providers.schema.json",
        "bitwarden": "bitwarden.schema.json"
    }
    
    if config_file not in schema_map:
        return {"valid": False, "error": f"Unknown config file: {config_file}"}
    
    # Load the config
    if config_file == "server":
        with open(CONFIG_PATH) as f:
            config = json.load(f)
    elif config_file == "bitwarden":
        config = load_bitwarden_config()
    else:
        with open(PROVIDERS_PATH) as f:
            config = json.load(f)
    
    # Validate
    is_valid, error = config_validator.validate(config, schema_map[config_file])
    return {"valid": is_valid, "error": error}