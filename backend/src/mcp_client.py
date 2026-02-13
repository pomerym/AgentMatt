"""
MCP Client

Provides minimal Model Context Protocol (MCP) client support for stdio and HTTP
transports, plus a manager for listing and calling tools.
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from .secret_resolver import resolve_config

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Raised when MCP requests fail."""


class MCPStdioClient:
    """JSON-RPC client over stdio for MCP servers."""

    def __init__(self, command: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None,
                 cwd: Optional[str] = None, timeout: int = 30):
        self.command = command
        self.args = args or []
        self.env = {**os.environ, **(env or {})}
        self.cwd = cwd
        self.timeout = timeout
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._request_id = 0
        self._initialized = False

    def _ensure_process(self) -> None:
        if self._process and self._process.poll() is None:
            return

        self._process = subprocess.Popen(
            [self.command, *self.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=self.cwd,
            env=self.env
        )
        self._initialized = False
        threading.Thread(target=self._drain_stderr, daemon=True).start()

    def _drain_stderr(self) -> None:
        if not self._process or not self._process.stderr:
            return
        for line in self._process.stderr:
            logger.warning("[MCP STDERR] %s", line.rstrip())

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send(self, payload: Dict[str, Any]) -> None:
        if not self._process or not self._process.stdin:
            raise MCPError("MCP stdio process not available")
        self._process.stdin.write(json.dumps(payload) + "\n")
        self._process.stdin.flush()

    def _read_response(self, request_id: int) -> Dict[str, Any]:
        if not self._process or not self._process.stdout:
            raise MCPError("MCP stdio process not available")

        start = time.time()
        while True:
            if time.time() - start > self.timeout:
                raise MCPError("Timed out waiting for MCP response")
            line = self._process.stdout.readline()
            if not line:
                raise MCPError("MCP server closed the connection")
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") == request_id:
                return message

    def _initialize(self) -> None:
        if self._initialized:
            return

        request_id = self._next_id()
        self._send({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "initialize",
            "params": {
                "clientInfo": {"name": "AgentMatt", "version": "1.0"},
                "protocolVersion": "2024-11-05"
            }
        })
        response = self._read_response(request_id)
        if "error" in response:
            raise MCPError(response["error"].get("message", "MCP initialize failed"))
        self._send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        self._initialized = True

    def request(self, method: str, params: Optional[Dict[str, Any]] = None, initialize: bool = True) -> Dict[str, Any]:
        with self._lock:
            self._ensure_process()
            if initialize:
                self._initialize()

            request_id = self._next_id()
            payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {}
            }
            self._send(payload)
            return self._read_response(request_id)


class MCPHttpClient:
    """JSON-RPC client over HTTP for MCP servers."""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30, verify_ssl: bool = True):
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._lock = threading.Lock()
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            request_id = self._next_id()
            payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {}
            }
            data = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json", **self.headers}
            
            # Debug logging
            if "Authorization" in headers:
                auth_value = headers["Authorization"]
                if len(auth_value) > 50:
                    logger.debug(f"[MCP HTTP] Authorization header: {auth_value[:30]}...{auth_value[-20:]}")
                else:
                    logger.debug(f"[MCP HTTP] Authorization header: {auth_value}")
            
            req = urllib.request.Request(self.url, data=data, headers=headers)
            
            # Create SSL context if needed
            context = None
            if self.url.startswith("https://") and not self.verify_ssl:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, timeout=self.timeout, context=context) as resp:
                response_data = resp.read().decode("utf-8")
            return json.loads(response_data)


class MCPManager:
    """Manages MCP servers and exposes tool listing/calling."""

    def __init__(self, config: Dict[str, Any]):
        resolved = resolve_config(config)
        self.servers: Dict[str, Dict[str, Any]] = {}
        for server in resolved.get("servers", []):
            if "id" in server:
                self.servers[server["id"]] = server
        self.tool_cache_ttl = int(resolved.get("tool_cache_ttl", 30))
        self._clients: Dict[str, Any] = {}
        self._tool_cache: Dict[str, Dict[str, Any]] = {}

    def list_servers(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": server_id,
                "name": server.get("name", server_id),
                "transport": server.get("transport"),
                "url": server.get("url")
            }
            for server_id, server in self.servers.items()
        ]

    def _get_client(self, server_id: str):
        if server_id in self._clients:
            return self._clients[server_id]

        if server_id not in self.servers:
            raise MCPError(f"Unknown MCP server: {server_id}")

        server = self.servers[server_id]
        transport = server.get("transport")
        if transport == "stdio":
            if not server.get("command"):
                raise MCPError(f"MCP server {server_id} missing command")
            client = MCPStdioClient(
                command=server.get("command", ""),
                args=server.get("args", []),
                env=server.get("env", {}),
                cwd=server.get("cwd")
            )
        elif transport == "http":
            if not server.get("url"):
                raise MCPError(f"MCP server {server_id} missing url")
            client = MCPHttpClient(
                url=server.get("url", ""),
                headers=server.get("headers", {}),
                verify_ssl=server.get("verify_ssl", True)
            )
        else:
            raise MCPError(f"Unsupported MCP transport: {transport}")

        self._clients[server_id] = client
        return client

    def _fetch_tools(self, server_id: str) -> List[Dict[str, Any]]:
        client = self._get_client(server_id)
        response = client.request("tools/list", {})
        if "error" in response:
            raise MCPError(response["error"].get("message", "MCP tools/list failed"))
        result = response.get("result", {})
        tools = result.get("tools", [])
        return tools

    def list_tools(self, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        now = time.time()
        server_ids = [server_id] if server_id else list(self.servers.keys())
        tools: List[Dict[str, Any]] = []

        for sid in server_ids:
            cached = self._tool_cache.get(sid)
            if cached and now - cached.get("fetched_at", 0) < self.tool_cache_ttl:
                server_tools = cached.get("tools", [])
            else:
                try:
                    server_tools = self._fetch_tools(sid)
                    self._tool_cache[sid] = {"tools": server_tools, "fetched_at": now}
                except Exception as exc:
                    logger.warning("Failed to list MCP tools for %s: %s", sid, exc)
                    server_tools = []

            for tool in server_tools:
                tools.append({
                    "server_id": sid,
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "inputSchema": tool.get("inputSchema")
                })

        return tools

    def call_tool(self, server_id: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        client = self._get_client(server_id)
        response = client.request("tools/call", {
            "name": tool_name,
            "arguments": arguments or {}
        })
        if "error" in response:
            raise MCPError(response["error"].get("message", "MCP tools/call failed"))
        return response.get("result", {})
