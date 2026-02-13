import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

function ChatApp() {
  const [sessionId, setSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [provider, setProvider] = useState('copilot');
  const [providers, setProviders] = useState([]);
  const [plugins, setPlugins] = useState([]);
  const [mcpServers, setMcpServers] = useState([]);
  const [mcpTools, setMcpTools] = useState([]);
  const [mcpEditMode, setMcpEditMode] = useState(false);
  const [mcpEditServer, setMcpEditServer] = useState(null);
  const [mcpFormData, setMcpFormData] = useState({
    id: '',
    name: '',
    transport: 'http',
    url: '',
    command: '',
    args: '',
    cwd: '',
    env: '',
    headers: '',
    verify_ssl: true
  });
  const [showSettings, setShowSettings] = useState(false);
  
  // AWS Bedrock configuration state
  const [bedrockConfig, setBedrockConfig] = useState({
    enabled: false,
    region: 'us-east-1',
    access_key_id: '',
    secret_access_key: '',
    session_token: '',
    model_id: 'anthropic.claude-3-sonnet-20240229-v1:0',
    anthropic_version: 'bedrock-2023-05-31',
    max_tokens: 4096,
    temperature: 0.7
  });
  const [bedrockModels, setBedrockModels] = useState([]);
  const [bedrockRegions, setBedrockRegions] = useState([]);
  const [settingsTab, setSettingsTab] = useState('general');
  const [saveStatus, setSaveStatus] = useState(null);
  const [saveError, setSaveError] = useState(null);
  const [messageError, setMessageError] = useState(null);
  const [isSending, setIsSending] = useState(false);
  const [hoveredSessionId, setHoveredSessionId] = useState(null);
  const [pendingApproval, setPendingApproval] = useState(false);
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [expandedOutputs, setExpandedOutputs] = useState({});
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);

  const markdownComponents = {
    p: ({ node, ...props }) => <p style={{ margin: '0 0 0.6rem 0' }} {...props} />,
    ul: ({ node, ...props }) => <ul style={{ margin: '0 0 0.6rem 1.2rem', padding: 0 }} {...props} />,
    ol: ({ node, ...props }) => <ol style={{ margin: '0 0 0.6rem 1.2rem', padding: 0 }} {...props} />,
    li: ({ node, ...props }) => <li style={{ margin: '0 0 0.2rem 0' }} {...props} />,
    h1: ({ node, ...props }) => <h1 style={{ margin: '0 0 0.6rem 0', fontSize: '1.1rem' }} {...props} />,
    h2: ({ node, ...props }) => <h2 style={{ margin: '0 0 0.6rem 0', fontSize: '1.05rem' }} {...props} />,
    h3: ({ node, ...props }) => <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1rem' }} {...props} />,
    a: ({ node, ...props }) => (
      <a
        {...props}
        target="_blank"
        rel="noopener noreferrer"
        style={{ color: '#90caf9' }}
      />
    ),
    code: ({ inline, children, ...props }) => (
      inline ?
        <code style={{ background: '#0d1a2f', padding: '0.1rem 0.3rem', borderRadius: 4 }} {...props}>
          {children}
        </code>
      :
        <pre style={{ background: '#0d1a2f', padding: '0.6rem', borderRadius: 6, overflowX: 'auto' }}>
          <code {...props}>{children}</code>
        </pre>
    )
  };

  useEffect(() => {
    // Fetch provider list
    fetch('/api/provider/list')
      .then(r => {
        if (!r.ok) throw new Error(`Provider list failed: ${r.status}`);
        return r.json();
      })
      .then(d => {
        setProviders(d.providers || []);
        if (d.active) setProvider(d.active);
      })
      .catch(e => console.error('Error fetching providers:', e));

    // Fetch plugins
    fetch('/api/plugins')
      .then(r => {
        if (!r.ok) throw new Error(`Plugins failed: ${r.status}`);
        return r.json();
      })
      .then(d => setPlugins(d.plugins || []))
      .catch(e => console.error('Error fetching plugins:', e));

    // Fetch MCP servers
    fetchMcpServers();

    // Fetch MCP tools (summary view)
    fetch('/api/mcp/tools?summary=true')
      .then(r => {
        if (!r.ok) throw new Error(`MCP tools failed: ${r.status}`);
        return r.json();
      })
      .then(d => setMcpTools(d.servers || []))
      .catch(e => console.error('Error fetching MCP tools:', e));

    // Fetch provider config
    fetch('/api/provider/config')
      .then(r => {
        if (!r.ok) throw new Error(`Config failed: ${r.status}`);
        return r.json();
      })
      .then(d => {
        if (d.providers?.aws_bedrock) {
          setBedrockConfig(d.providers.aws_bedrock);
        }
      })
      .catch(e => console.error('Error fetching config:', e));

    // Fetch Bedrock models
    fetch('/api/provider/bedrock/models')
      .then(r => {
        if (!r.ok) throw new Error(`Models failed: ${r.status}`);
        return r.json();
      })
      .then(d => {
        console.log('Bedrock models loaded:', d.models?.length || 0);
        setBedrockModels(d.models || []);
      })
      .catch(e => console.error('Error fetching models:', e));

    // Fetch Bedrock regions
    fetch('/api/provider/bedrock/regions')
      .then(r => {
        if (!r.ok) throw new Error(`Regions failed: ${r.status}`);
        return r.json();
      })
      .then(d => {
        console.log('Bedrock regions loaded:', d.regions?.length || 0);
        setBedrockRegions(d.regions || []);
      })
      .catch(e => console.error('Error fetching regions:', e));
  }, []);

  // Load sessions on mount, auto-select latest or create a new one
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const res = await fetch('/api/chat/sessions');
        if (!res.ok) throw new Error(`Sessions failed: ${res.status}`);
        const data = await res.json();
        const existing = data.sessions || [];
        if (existing.length > 0) {
            const mapped = existing.map((s, idx) => ({
              id: s.session_id,
              name: s.name || `Session ${existing.length - idx}`
          }));
          setSessions(mapped);
          selectSession(existing[0].session_id);
          return;
        }
      } catch (e) {
        console.error('Error fetching sessions:', e);
      }

      console.log('[Auto-Session] No sessions found, auto-starting new session...');
      startSession();
    };

    loadSessions();
  }, []); // Run only on mount

  useEffect(() => {
    const lastAssistant = [...messages].reverse().find(m => m.sender === 'assistant');
    const needsApproval = Boolean(
      lastAssistant &&
      typeof lastAssistant.content === 'string' &&
      lastAssistant.content.includes('Approval required')
    );
    setPendingApproval(needsApproval);
  }, [messages]);

  useEffect(() => {
    if (!autoScrollEnabled || !messagesEndRef.current) return;
    requestAnimationFrame(() => {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    });
  }, [messages, isSending, pendingApproval, autoScrollEnabled]);

  const handleMessagesScroll = () => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    const atBottom = distanceFromBottom <= 40;
    setAutoScrollEnabled(atBottom);
    setShowScrollButton(!atBottom);
  };

  const scrollToBottom = () => {
    setAutoScrollEnabled(true);
    setShowScrollButton(false);
    if (!messagesEndRef.current) return;
    messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
  };

  const isCommandOutput = (msg) => {
    if (msg.sender !== 'assistant' || typeof msg.content !== 'string') return false;
    const trimmed = msg.content.trimStart();
    if (!trimmed.startsWith('$ ')) return false;
    return trimmed.includes('\n');
  };

  const toggleOutput = (key) => {
    setExpandedOutputs(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const saveBedrockConfig = async () => {
    setSaveStatus('saving');
    setSaveError(null);
    console.log('[AWS Bedrock] Saving configuration:', bedrockConfig);
    
    try {
      const payload = { provider_id: 'aws_bedrock', config: bedrockConfig };
      console.log('[AWS Bedrock] Request payload:', JSON.stringify(payload, null, 2));
      
      const res = await fetch('/api/provider/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      console.log('[AWS Bedrock] Response status:', res.status, res.statusText);
      
      const data = await res.json();
      console.log('[AWS Bedrock] Response data:', JSON.stringify(data, null, 2));
      
      if (!res.ok) {
        const errorMsg = data.message || 'Unknown error';
        console.error('[AWS Bedrock] HTTP error:', res.status, '-', errorMsg);
        setSaveError(errorMsg);
        setSaveStatus('error');
        return;
      }
      
      if (data.status === 'updated') {
        console.log('[AWS Bedrock] Configuration saved successfully');
        setSaveStatus('saved');
        setSaveError(null);
        setTimeout(() => setSaveStatus(null), 2000);
      } else {
        const errorMsg = data.message || 'Unknown error';
        console.error('[AWS Bedrock] Save failed - unexpected status:', data.status);
        console.error('[AWS Bedrock] Error message:', errorMsg);
        setSaveError(errorMsg);
        setSaveStatus('error');
      }
    } catch (e) {
      const errorMsg = e.message || 'Network error or invalid response';
      console.error('[AWS Bedrock] Exception during save:', errorMsg);
      console.error('[AWS Bedrock] Full error:', e);
      setSaveError(errorMsg);
      setSaveStatus('error');
    }
  };

  const startSession = async () => {
    console.log('[Session] Starting new session');
    try {
      const res = await fetch('/api/chat/start', { method: 'POST' });
      console.log('[Session] Start response status:', res.status);
      
      const data = await res.json();
      console.log('[Session] Start response data:', data);
      
      if (!res.ok) {
        console.error('[Session] Failed to start session:', data.error);
        setMessageError('Failed to start session: ' + (data.error || 'Unknown error'));
        return;
      }
      
      const newSessionId = data.session_id;
      console.log('[Session] New session created:', newSessionId);
      
      setSessionId(newSessionId);
          const newSessionName = data.name || `Session ${sessions.length + 1}`;
          setSessions([...sessions, { id: newSessionId, name: newSessionName }]);
      
      // Fetch initial history
      console.log('[Session] Fetching initial history for', newSessionId);
      const histRes = await fetch(`/api/chat/${newSessionId}/history`);
      console.log('[Session] History response status:', histRes.status);
      
      const histData = await histRes.json();
      console.log('[Session] Initial history:', histData);
      
      setMessages(histData.history || []);
      console.log('[Session] Session initialized successfully');
      
    } catch (e) {
      console.error('[Session] Exception while starting session:', e.message);
      console.error('[Session] Full error:', e);
      setMessageError('Failed to start session: ' + (e.message || 'Network error'));
    }
  };

  const renameSession = async (id) => {
    const currentName = sessions.find(s => s.id === id)?.name || '';
    const nextNameRaw = window.prompt('Rename session', currentName);
    if (nextNameRaw === null) return;
    const nextName = nextNameRaw.trim();
    if (!nextName) return;

    try {
      const res = await fetch(`/api/chat/${id}/rename`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: nextName })
      });
      const data = await res.json();
      if (!res.ok) {
        setMessageError(data.error || data.message || 'Failed to rename session');
        return;
      }

      setSessions(prev => prev.map(s => (s.id === id ? { ...s, name: nextName } : s)));
    } catch (e) {
      setMessageError('Failed to rename session: ' + (e.message || 'Network error'));
    }
  };

  const fetchMcpServers = async () => {
    try {
      const res = await fetch('/api/mcp/servers');
      if (!res.ok) throw new Error(`MCP servers failed: ${res.status}`);
      const data = await res.json();
      setMcpServers(data.servers || []);
    } catch (e) {
      console.error('Error fetching MCP servers:', e);
    }
  };

  const openMcpAddForm = () => {
    setMcpFormData({
      id: '',
      name: '',
      transport: 'http',
      url: '',
      command: '',
      args: '',
      cwd: '',
      env: '',
      headers: '',
      verify_ssl: true
    });
    setMcpEditServer(null);
    setMcpEditMode(true);
  };

  const openMcpEditForm = (server) => {
    setMcpFormData({
      id: server.id || '',
      name: server.name || '',
      transport: server.transport || 'http',
      url: server.url || '',
      command: server.command || '',
      args: (server.args || []).join(' '),
      cwd: server.cwd || '',
      env: JSON.stringify(server.env || {}, null, 2),
      headers: JSON.stringify(server.headers || {}, null, 2),
      verify_ssl: server.verify_ssl !== undefined ? server.verify_ssl : true
    });
    setMcpEditServer(server.id);
    setMcpEditMode(true);
  };

  const saveMcpServer = async () => {
    try {
      const payload = {
        id: mcpFormData.id.trim(),
        name: mcpFormData.name.trim(),
        transport: mcpFormData.transport
      };

      if (mcpFormData.transport === 'http') {
        payload.url = mcpFormData.url.trim();
        payload.verify_ssl = mcpFormData.verify_ssl;
        if (mcpFormData.headers) {
          payload.headers = JSON.parse(mcpFormData.headers);
        }
      } else {
        payload.command = mcpFormData.command.trim();
        if (mcpFormData.args) {
          payload.args = mcpFormData.args.split(/\s+/).filter(Boolean);
        }
        if (mcpFormData.cwd) {
          payload.cwd = mcpFormData.cwd.trim();
        }
        if (mcpFormData.env) {
          payload.env = JSON.parse(mcpFormData.env);
        }
      }

      const res = await fetch('/api/mcp/server', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.error || 'Failed to save MCP server');
        return;
      }

      setMcpEditMode(false);
      fetchMcpServers();
      setTimeout(() => {
        fetch('/api/mcp/tools?summary=true')
          .then(r => r.json())
          .then(d => setMcpTools(d.servers || []));
      }, 500);
    } catch (e) {
      alert('Failed to save MCP server: ' + (e.message || 'Invalid JSON'));
    }
  };

  const deleteMcpServer = async (serverId) => {
    if (!window.confirm(`Delete MCP server "${serverId}"?`)) return;
    try {
      const res = await fetch(`/api/mcp/server/${serverId}`, { method: 'DELETE' });
      const data = await res.json();
      if (!res.ok) {
        alert(data.error || 'Failed to delete MCP server');
        return;
      }
      fetchMcpServers();
      setTimeout(() => {
        fetch('/api/mcp/tools?summary=true')
          .then(r => r.json())
          .then(d => setMcpTools(d.servers || []));
      }, 500);
    } catch (e) {
      alert('Failed to delete MCP server: ' + e.message);
    }
  };

  const selectSession = async (id) => {
    console.log('[Session] Selecting session:', id);
    setSessionId(id);
    setMessageError(null);
    
    try {
      console.log('[Session] Fetching history for', id);
      const histRes = await fetch(`/api/chat/${id}/history`);
      console.log('[Session] History response status:', histRes.status);
      
      const histData = await histRes.json();
      console.log('[Session] Session history:', histData);
      
      if (!histRes.ok) {
        console.error('[Session] Failed to fetch history:', histData.error);
        setMessageError('Failed to load session: ' + (histData.error || 'Unknown error'));
        return;
      }
      
      setMessages(histData.history || []);
      console.log('[Session] Session loaded successfully with', histData.history?.length || 0, 'messages');
      
    } catch (e) {
      console.error('[Session] Exception while selecting session:', e.message);
      console.error('[Session] Full error:', e);
      setMessageError('Failed to load session: ' + (e.message || 'Network error'));
    }
  };

  const sendMessage = async (overrideContent = null) => {
    const content = (overrideContent ?? input).trim();
    if (!sessionId || !content) {
      console.log('[Chat] Skipping send - sessionId:', sessionId, 'input:', input);
      return;
    }

    const messageContent = content;
    console.log('[Chat] Sending message:', { sessionId, messageContent });
    setMessageError(null);
    setIsSending(true);
    
    // Optimistically add to UI
    const userMessage = { sender: 'user', content: messageContent };
    setMessages([...messages, userMessage]);
    if (overrideContent === null) {
      setInput('');
    }
    
    try {
      const payload = { message: messageContent };
      console.log('[Chat] POST payload:', JSON.stringify(payload));
      
      const res = await fetch(`/api/chat/${sessionId}/message`, {
        method: 'POST',
        body: JSON.stringify(payload),
        headers: { 'Content-Type': 'application/json' }
      });
      
      console.log('[Chat] Message response status:', res.status, res.statusText);
      
      const data = await res.json();
      console.log('[Chat] Message response data:', JSON.stringify(data, null, 2));
      
      if (!res.ok) {
        const errorMsg = data.error || data.message || 'Failed to send message';
        console.error('[Chat] HTTP error sending message:', res.status, '-', errorMsg);
        setMessageError(errorMsg);
        return;
      }
      
      // Fetch updated history
      console.log('[Chat] Fetching updated history after message');
      const histRes = await fetch(`/api/chat/${sessionId}/history`);
      console.log('[Chat] History response status:', histRes.status);
      
      const histData = await histRes.json();
      console.log('[Chat] Updated history:', JSON.stringify(histData, null, 2));
      
      if (!histRes.ok) {
        console.error('[Chat] Failed to fetch updated history:', histRes.status);
        setMessageError('Failed to fetch chat history');
        return;
      }
      
      setMessages(histData.history || [userMessage]);
      console.log('[Chat] Chat history updated successfully');
      
    } catch (e) {
      const errorMsg = e.message || 'Network error';
      console.error('[Chat] Exception while sending message:', errorMsg);
      console.error('[Chat] Full error:', e);
      setMessageError(errorMsg);
      // Keep the message in UI since user typed it
    } finally {
      setIsSending(false);
    }
  };

  const approveCommand = () => sendMessage('/approve');
  const approveByCommand = () => sendMessage('/approve command');
  const approveBySubcommand = () => sendMessage('/approve command-subcommand');
  const approveExact = () => sendMessage('/approve exact');
  const denyCommand = () => sendMessage('/deny');

  const closeSession = async (id) => {
    try {
      const res = await fetch(`/api/chat/${id}/close`, { method: 'POST' });
      if (!res.ok) throw new Error(`Close failed: ${res.status}`);
      const remaining = sessions.filter(s => s.id !== id);
      setSessions(remaining);
      if (sessionId === id) {
        if (remaining.length > 0) {
          selectSession(remaining[0].id);
        } else {
          setSessionId(null);
          setMessages([]);
          startSession();
        }
      }
    } catch (e) {
      console.error('Error closing session:', e);
      setMessageError('Failed to close session: ' + (e.message || 'Unknown error'));
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', fontFamily: 'Segoe UI, Arial, sans-serif', background: '#0d1a2f' }}>
      {/* Sidebar */}
      <aside style={{
        width: 260,
        background: 'linear-gradient(180deg, #102040 0%, #0d1a2f 100%)',
        color: 'white',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden',
        borderRight: '1px solid #233a5e'
      }}>
        <div style={{ padding: '1.5rem 1rem', borderBottom: '1px solid #233a5e', display: 'flex', alignItems: 'center', gap: 12 }}>
          <svg width="36" height="36" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="24" cy="24" r="22" fill="#233a5e" stroke="#0d47a1" strokeWidth="3"/>
            <ellipse cx="24" cy="28" rx="10" ry="6" fill="#0d47a1"/>
            <circle cx="18" cy="22" r="2.5" fill="#fff"/>
            <circle cx="30" cy="22" r="2.5" fill="#fff"/>
            <rect x="20" y="32" width="8" height="2.5" rx="1.25" fill="#fff"/>
          </svg>
          <span style={{ fontWeight: 700, fontSize: '1.25rem', letterSpacing: 1 }}>AgentMatt</span>
        </div>
        <button
          onClick={startSession}
          style={{
            margin: '1rem',
            padding: '0.75rem 1rem',
            background: 'linear-gradient(90deg, #0d47a1 60%, #233a5e 100%)',
            color: 'white',
            border: 'none',
            borderRadius: 8,
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 2px 8px #0d47a133'
          }}
        >
          + New Session
        </button>
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 0.5rem', minHeight: 0 }}>
          <div style={{ fontSize: '0.85rem', color: '#42a5f5', marginBottom: 8, marginLeft: 8 }}>Sessions</div>
          {sessions.map(s => (
            <div
              key={s.id}
              onClick={() => selectSession(s.id)}
              onMouseEnter={() => setHoveredSessionId(s.id)}
              onMouseLeave={() => setHoveredSessionId(null)}
              style={{
                padding: '0.6rem 0.8rem',
                borderRadius: 6,
                marginBottom: 4,
                background: sessionId === s.id ? '#0d47a1' : 'transparent',
                cursor: 'pointer',
                fontWeight: sessionId === s.id ? 600 : 400,
                color: sessionId === s.id ? 'white' : '#b3d1ff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 8
              }}
            >
              <span>{s.name}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    renameSession(s.id);
                  }}
                  title="Rename session"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#b3d1ff',
                    fontSize: '0.95rem',
                    cursor: 'pointer',
                    opacity: hoveredSessionId === s.id ? 1 : 0.75,
                    transition: 'opacity 0.15s ease'
                  }}
                >
                  ✎
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    closeSession(s.id);
                  }}
                  title="Close session"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#b3d1ff',
                    fontSize: '0.95rem',
                    cursor: 'pointer',
                    opacity: hoveredSessionId === s.id ? 1 : 0.75,
                    transition: 'opacity 0.15s ease'
                  }}
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
        <div style={{ padding: '1rem', borderTop: '1px solid #233a5e' }}>
          <div style={{ fontSize: '0.85rem', color: '#42a5f5', marginBottom: 8 }}>Provider</div>
          <select
            value={provider}
            onChange={e => setProvider(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem',
              borderRadius: 6,
              border: '1px solid #233a5e',
              background: '#1a2740',
              color: 'white',
              fontWeight: 500
            }}
          >
            {providers.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div style={{ padding: '1rem', borderTop: '1px solid #233a5e' }}>
          <div style={{ fontSize: '0.85rem', color: '#42a5f5', marginBottom: 8 }}>Plugins</div>
          {plugins.length === 0 && <div style={{ color: '#6b7a99', fontSize: '0.9rem' }}>No plugins loaded</div>}
          {plugins.map(p => (
            <div key={p.name} style={{ color: '#b3d1ff', fontSize: '0.9rem', marginBottom: 4 }}>{p.name} <span style={{ color: '#6b7a99' }}>v{p.version}</span></div>
          ))}
        </div>
        <div style={{ padding: '1rem', borderTop: '1px solid #233a5e' }}>
          <div style={{ fontSize: '0.85rem', color: '#42a5f5', marginBottom: 8 }}>Tools</div>
          {mcpServers.length === 0 && (
            <div style={{ color: '#6b7a99', fontSize: '0.9rem' }}>
              No MCP servers configured
            </div>
          )}
          {mcpServers.length > 0 && mcpTools.length === 0 && (
            <div style={{ color: '#6b7a99', fontSize: '0.9rem' }}>
              No MCP tools available
            </div>
          )}
          {mcpTools.map(server => (
            <div
              key={server.server_id}
              style={{ color: '#b3d1ff', fontSize: '0.88rem', marginBottom: 6 }}
            >
              {server.server_id}: {server.tool_count} tool{server.tool_count !== 1 ? 's' : ''}
              {server.error ? <span style={{ color: '#ff6b6b' }}> - {server.error}</span> : null}
            </div>
          ))}
          <div style={{ color: '#6b7a99', fontSize: '0.82rem', marginTop: 6 }}>
            Use /mcp list or /mcp &lt;server&gt; &lt;tool&gt; {"{...}"}
          </div>
        </div>
        <div style={{ padding: '1rem', borderTop: '1px solid #233a5e' }}>
          <button
            onClick={() => setShowSettings(!showSettings)}
            style={{
              width: '100%',
              padding: '0.5rem',
              borderRadius: 6,
              border: '1px solid #233a5e',
              background: showSettings ? '#0d47a1' : '#1a2740',
              color: 'white',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
            Settings
          </button>
        </div>
      </aside>
      {/* Main Chat Area */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', background: 'linear-gradient(135deg, #0d1a2f 0%, #233a5e 100%)', position: 'relative' }}>
        <header style={{
          background: 'linear-gradient(90deg, #0d47a1 60%, #102040 100%)',
          color: 'white',
          padding: '1rem 2rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 2px 8px #0d47a133'
        }}>
          <span style={{ fontWeight: 600, fontSize: '1.1rem' }}>
            {sessionId
              ? `Session: ${(sessions.find(s => s.id === sessionId)?.name) || sessionId}`
              : 'No session selected'}
          </span>
          <span style={{ opacity: 0.7, fontSize: '0.95rem' }}>Provider: {provider}</span>
        </header>
        <div
          ref={messagesContainerRef}
          onScroll={handleMessagesScroll}
          style={{ flex: 1, overflowY: 'auto', padding: '2rem', display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0 }}
        >
          {messages.length === 0 && (
            <div style={{ color: '#42a5f5', opacity: 0.7, textAlign: 'center', marginTop: 48, fontSize: '1.1rem' }}>
              {sessionId ? 'No messages yet. Start the conversation!' : 'Select or start a session to begin.'}
            </div>
          )}
          {messages.map((msg, idx) => (
            <div key={idx} style={{
              alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '70%',
              padding: '0.75rem 1rem',
              borderRadius: 12,
              background: msg.sender === 'user' ? '#0d47a1' : '#233a5e',
              color: 'white',
              fontWeight: msg.sender === 'user' ? 600 : 400,
              boxShadow: '0 2px 8px #0d47a122'
            }}>
              {isCommandOutput(msg) ? (() => {
                const key = msg.id || idx;
                const expanded = Boolean(expandedOutputs[key]);
                return (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                      <span style={{ color: '#90caf9', fontSize: '0.85rem' }}>
                        Command output hidden
                      </span>
                      <button
                        type="button"
                        onClick={() => toggleOutput(key)}
                        style={{
                          background: 'transparent',
                          border: '1px solid #3b527a',
                          color: '#b3d1ff',
                          borderRadius: 6,
                          padding: '0.2rem 0.5rem',
                          fontSize: '0.8rem',
                          cursor: 'pointer'
                        }}
                      >
                        {expanded ? 'Hide output' : 'Show output'}
                      </button>
                    </div>
                    {expanded && (
                      <pre style={{ background: '#0d1a2f', padding: '0.6rem', borderRadius: 6, overflowX: 'auto', margin: 0 }}>
                        <code>{msg.content}</code>
                      </pre>
                    )}
                  </div>
                );
              })() : (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkBreaks]}
                  components={markdownComponents}
                >
                  {msg.content}
                </ReactMarkdown>
              )}
            </div>
          ))}
          {isSending && (
            <div style={{
              alignSelf: 'flex-start',
              maxWidth: '70%',
              padding: '0.6rem 0.9rem',
              borderRadius: 12,
              background: '#1a2740',
              color: '#b3d1ff',
              fontSize: '0.95rem',
              boxShadow: '0 2px 8px #0d47a122'
            }}>
              AgentMatt is thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        {showScrollButton && (
          <button
            type="button"
            onClick={scrollToBottom}
            style={{
              position: 'absolute',
              right: 24,
              bottom: 96,
              padding: '0.5rem 0.9rem',
              borderRadius: 999,
              border: '1px solid #233a5e',
              background: '#102040',
              color: '#90caf9',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 6px 18px #0d47a144'
            }}
          >
            Jump to latest
          </button>
        )}
        {/* Message Error Display */}
        {messageError && (
          <div style={{
            padding: '0.75rem 1rem',
            background: '#c62828',
            color: '#ffcdd2',
            fontSize: '0.9rem',
            borderTop: '1px solid #ff5252',
            wordWrap: 'break-word'
          }}>
            <strong>Error:</strong> {messageError}
          </div>
        )}
        {pendingApproval && (
          <div style={{
            padding: '0.5rem 1rem',
            background: '#18233b',
            borderTop: '1px solid #233a5e',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: 10
          }}>
            <span style={{ color: '#90caf9', fontSize: '0.9rem' }}>
              Approval required
            </span>
            <button
              type="button"
              onClick={approveCommand}
              style={{
                padding: '0.35rem 0.8rem',
                borderRadius: 6,
                border: '1px solid #2e7d32',
                background: '#2e7d32',
                color: 'white',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Approve
            </button>
            <button
              type="button"
              onClick={approveByCommand}
              style={{
                padding: '0.35rem 0.7rem',
                borderRadius: 6,
                border: '1px solid #1e88e5',
                background: '#1e88e5',
                color: 'white',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Approve Command
            </button>
            <button
              type="button"
              onClick={approveBySubcommand}
              style={{
                padding: '0.35rem 0.7rem',
                borderRadius: 6,
                border: '1px solid #1565c0',
                background: '#1565c0',
                color: 'white',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Approve Subcommand
            </button>
            <button
              type="button"
              onClick={approveExact}
              style={{
                padding: '0.35rem 0.7rem',
                borderRadius: 6,
                border: '1px solid #0d47a1',
                background: '#0d47a1',
                color: 'white',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Approve Exact
            </button>
            <button
              type="button"
              onClick={denyCommand}
              style={{
                padding: '0.35rem 0.8rem',
                borderRadius: 6,
                border: '1px solid #c62828',
                background: 'transparent',
                color: '#ef9a9a',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Deny
            </button>
          </div>
        )}
        <form
          onSubmit={e => { e.preventDefault(); sendMessage(); }}
          style={{
            display: 'flex',
            gap: 12,
            padding: '1rem 2rem',
            background: '#102040',
            borderTop: '1px solid #233a5e'
          }}
        >
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            style={{
              flex: 1,
              padding: '0.75rem 1rem',
              borderRadius: 8,
              border: '1px solid #233a5e',
              background: '#1a2740',
              color: 'white',
              fontSize: '1rem',
              outline: 'none'
            }}
            disabled={!sessionId}
          />
          <button
            type="submit"
            style={{
              padding: '0.75rem 1.5rem',
              borderRadius: 8,
              border: 'none',
              background: 'linear-gradient(90deg, #0d47a1 60%, #233a5e 100%)',
              color: 'white',
              fontWeight: 600,
              cursor: sessionId ? 'pointer' : 'not-allowed',
              opacity: sessionId ? 1 : 0.5
            }}
            disabled={!sessionId}
          >
            Send
          </button>
        </form>
      </main>
      {/* Settings Panel */}
      {showSettings && (
        <aside style={{
          width: 340,
          background: '#102040',
          color: 'white',
          borderLeft: '1px solid #233a5e',
          padding: '1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          overflowY: 'auto'
        }}>
          <h3 style={{ margin: 0, fontWeight: 700 }}>Settings</h3>
          
          {/* Settings Tabs */}
          <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid #233a5e', paddingBottom: 8 }}>
            <button
              onClick={() => setSettingsTab('general')}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: 6,
                border: 'none',
                background: settingsTab === 'general' ? '#0d47a1' : 'transparent',
                color: 'white',
                cursor: 'pointer',
                fontWeight: settingsTab === 'general' ? 600 : 400
              }}
            >
              General
            </button>
            <button
              onClick={() => setSettingsTab('providers')}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: 6,
                border: 'none',
                background: settingsTab === 'providers' ? '#0d47a1' : 'transparent',
                color: 'white',
                cursor: 'pointer',
                fontWeight: settingsTab === 'providers' ? 600 : 400
              }}
            >
              AI Providers
            </button>
            <button
              onClick={() => setSettingsTab('mcp')}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: 6,
                border: 'none',
                background: settingsTab === 'mcp' ? '#0d47a1' : 'transparent',
                color: 'white',
                cursor: 'pointer',
                fontWeight: settingsTab === 'mcp' ? 600 : 400
              }}
            >
              MCP Servers
            </button>
          </div>

          {/* General Settings Tab */}
          {settingsTab === 'general' && (
            <>
              <div>
                <label style={{ fontSize: '0.9rem', color: '#42a5f5' }}>API Base URL</label>
                <input
                  defaultValue="http://localhost:8000/api"
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    borderRadius: 6,
                    border: '1px solid #233a5e',
                    background: '#1a2740',
                    color: 'white',
                    marginTop: 4,
                    boxSizing: 'border-box'
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.9rem', color: '#42a5f5' }}>Theme</label>
                <select
                  defaultValue="dark"
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    borderRadius: 6,
                    border: '1px solid #233a5e',
                    background: '#1a2740',
                    color: 'white',
                    marginTop: 4,
                    boxSizing: 'border-box'
                  }}
                >
                  <option value="dark">Dark</option>
                  <option value="light">Light</option>
                </select>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <label style={{ fontSize: '0.9rem', color: '#42a5f5' }}>Notifications</label>
                <input type="checkbox" defaultChecked />
              </div>
            </>
          )}

          {/* AI Providers Tab */}
          {settingsTab === 'providers' && (
            <>
              <div style={{ 
                background: '#1a2740', 
                borderRadius: 8, 
                padding: '1rem',
                border: '1px solid #233a5e'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <h4 style={{ margin: 0, color: '#42a5f5', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: '1.2rem' }}>☁️</span> AWS Bedrock
                  </h4>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                    <span style={{ fontSize: '0.8rem', color: bedrockConfig.enabled ? '#4caf50' : '#999' }}>
                      {bedrockConfig.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                    <input
                      type="checkbox"
                      checked={bedrockConfig.enabled}
                      onChange={e => setBedrockConfig({ ...bedrockConfig, enabled: e.target.checked })}
                      style={{ width: 18, height: 18, accentColor: '#0d47a1' }}
                    />
                  </label>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, opacity: bedrockConfig.enabled ? 1 : 0.5 }}>
                  {/* Region */}
                  <div>
                    <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>
                      AWS Region *
                    </label>
                    <select
                      value={bedrockConfig.region}
                      onChange={e => setBedrockConfig({ ...bedrockConfig, region: e.target.value })}
                      disabled={!bedrockConfig.enabled}
                      style={{
                        width: '100%',
                        padding: '0.5rem',
                        borderRadius: 6,
                        border: '1px solid #233a5e',
                        background: '#102040',
                        color: 'white',
                        boxSizing: 'border-box'
                      }}
                    >
                      {bedrockRegions.map(r => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </select>
                  </div>

                  {/* Access Key ID */}
                  <div>
                    <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>
                      Access Key ID *
                    </label>
                    <input
                      type="password"
                      value={bedrockConfig.access_key_id}
                      onChange={e => setBedrockConfig({ ...bedrockConfig, access_key_id: e.target.value })}
                      disabled={!bedrockConfig.enabled}
                      placeholder="AKIA..."
                      style={{
                        width: '100%',
                        padding: '0.5rem',
                        borderRadius: 6,
                        border: '1px solid #233a5e',
                        background: '#102040',
                        color: 'white',
                        boxSizing: 'border-box'
                      }}
                    />
                  </div>

                  {/* Secret Access Key */}
                  <div>
                    <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>
                      Secret Access Key *
                    </label>
                    <input
                      type="password"
                      value={bedrockConfig.secret_access_key}
                      onChange={e => setBedrockConfig({ ...bedrockConfig, secret_access_key: e.target.value })}
                      disabled={!bedrockConfig.enabled}
                      placeholder="Your secret key"
                      style={{
                        width: '100%',
                        padding: '0.5rem',
                        borderRadius: 6,
                        border: '1px solid #233a5e',
                        background: '#102040',
                        color: 'white',
                        boxSizing: 'border-box'
                      }}
                    />
                  </div>

                  {/* Session Token (optional) */}
                  <div>
                    <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>
                      Session Token <span style={{ color: '#666' }}>(optional, for temporary credentials)</span>
                    </label>
                    <input
                      type="password"
                      value={bedrockConfig.session_token}
                      onChange={e => setBedrockConfig({ ...bedrockConfig, session_token: e.target.value })}
                      disabled={!bedrockConfig.enabled}
                      placeholder="Optional session token"
                      style={{
                        width: '100%',
                        padding: '0.5rem',
                        borderRadius: 6,
                        border: '1px solid #233a5e',
                        background: '#102040',
                        color: 'white',
                        boxSizing: 'border-box'
                      }}
                    />
                  </div>

                  {/* Model Selection */}
                  <div>
                    <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>
                      Model *
                    </label>
                    <select
                      value={bedrockConfig.model_id}
                      onChange={e => setBedrockConfig({ ...bedrockConfig, model_id: e.target.value })}
                      disabled={!bedrockConfig.enabled}
                      style={{
                        width: '100%',
                        padding: '0.5rem',
                        borderRadius: 6,
                        border: '1px solid #233a5e',
                        background: '#102040',
                        color: 'white',
                        boxSizing: 'border-box'
                      }}
                    >
                      {bedrockModels.map(m => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                  </div>

                  {/* Advanced Settings */}
                  <div style={{ borderTop: '1px solid #233a5e', paddingTop: 10, marginTop: 4 }}>
                    <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: 8 }}>Advanced Settings</div>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                      <div style={{ gridColumn: '1 / -1' }}>
                        <label style={{ fontSize: '0.75rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>
                          Anthropic Version
                        </label>
                        <input
                          type="text"
                          value={bedrockConfig.anthropic_version || ''}
                          onChange={e => setBedrockConfig({ ...bedrockConfig, anthropic_version: e.target.value })}
                          disabled={!bedrockConfig.enabled}
                          placeholder="bedrock-2023-05-31"
                          style={{
                            width: '100%',
                            padding: '0.4rem',
                            borderRadius: 6,
                            border: '1px solid #233a5e',
                            background: '#102040',
                            color: 'white',
                            boxSizing: 'border-box'
                          }}
                        />
                      </div>
                      {/* Max Tokens */}
                      <div>
                        <label style={{ fontSize: '0.75rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>
                          Max Tokens
                        </label>
                        <input
                          type="number"
                          value={bedrockConfig.max_tokens}
                          onChange={e => setBedrockConfig({ ...bedrockConfig, max_tokens: parseInt(e.target.value) || 4096 })}
                          disabled={!bedrockConfig.enabled}
                          min="1"
                          max="200000"
                          style={{
                            width: '100%',
                            padding: '0.4rem',
                            borderRadius: 6,
                            border: '1px solid #233a5e',
                            background: '#102040',
                            color: 'white',
                            boxSizing: 'border-box'
                          }}
                        />
                      </div>

                      {/* Temperature */}
                      <div>
                        <label style={{ fontSize: '0.75rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>
                          Temperature
                        </label>
                        <input
                          type="number"
                          value={bedrockConfig.temperature}
                          onChange={e => setBedrockConfig({ ...bedrockConfig, temperature: parseFloat(e.target.value) || 0.7 })}
                          disabled={!bedrockConfig.enabled}
                          min="0"
                          max="1"
                          step="0.1"
                          style={{
                            width: '100%',
                            padding: '0.4rem',
                            borderRadius: 6,
                            border: '1px solid #233a5e',
                            background: '#102040',
                            color: 'white',
                            boxSizing: 'border-box'
                          }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Save Button */}
                  <button
                    onClick={saveBedrockConfig}
                    disabled={!bedrockConfig.enabled}
                    style={{
                      marginTop: 8,
                      padding: '0.6rem 1rem',
                      borderRadius: 6,
                      border: 'none',
                      background: bedrockConfig.enabled ? 'linear-gradient(90deg, #0d47a1, #1565c0)' : '#333',
                      color: 'white',
                      fontWeight: 600,
                      cursor: bedrockConfig.enabled ? 'pointer' : 'not-allowed',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 8
                    }}
                  >
                    {saveStatus === 'saving' && '⏳ Saving...'}
                    {saveStatus === 'saved' && '✓ Saved!'}
                    {saveStatus === 'error' && '✗ Error'}
                    {!saveStatus && '💾 Save Configuration'}
                  </button>

                  {/* Error Message Display */}
                  {saveError && (
                    <div style={{
                      marginTop: 12,
                      padding: '0.75rem',
                      background: '#c62828',
                      color: '#ffcdd2',
                      borderRadius: 4,
                      fontSize: '0.85rem',
                      borderLeft: '3px solid #ff5252',
                      wordWrap: 'break-word'
                    }}>
                      <strong>Error:</strong> {saveError}
                    </div>
                  )}
                </div>
              </div>

              {/* Info box about other providers */}
              <div style={{ 
                background: '#0d1a2f', 
                borderRadius: 6, 
                padding: '0.75rem',
                border: '1px dashed #233a5e',
                fontSize: '0.8rem',
                color: '#666'
              }}>
                <strong style={{ color: '#42a5f5' }}>More providers coming soon:</strong>
                <ul style={{ margin: '8px 0 0 0', paddingLeft: 20 }}>
                  <li>GitHub Copilot</li>
                  <li>OpenAI</li>
                  <li>Azure OpenAI</li>
                  <li>Google Vertex AI</li>
                </ul>
              </div>
            </>
          )}

          {/* MCP Servers Tab */}
          {settingsTab === 'mcp' && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h4 style={{ margin: 0, color: '#42a5f5' }}>MCP Servers</h4>
                <button
                  onClick={openMcpAddForm}
                  style={{
                    padding: '0.4rem 0.8rem',
                    borderRadius: 6,
                    border: 'none',
                    background: '#0d47a1',
                    color: 'white',
                    fontWeight: 600,
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  + Add Server
                </button>
              </div>

              {!mcpEditMode && mcpServers.length === 0 && (
                <div style={{ color: '#6b7a99', fontSize: '0.9rem', textAlign: 'center', padding: '2rem' }}>
                  No MCP servers configured. Click "+ Add Server" to get started.
                </div>
              )}

              {!mcpEditMode && mcpServers.map(server => (
                <div
                  key={server.id}
                  style={{
                    background: '#1a2740',
                    borderRadius: 8,
                    padding: '1rem',
                    border: '1px solid #233a5e',
                    marginBottom: 12
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div>
                      <div style={{ color: 'white', fontWeight: 600, fontSize: '0.95rem' }}>{server.name || server.id}</div>
                      <div style={{ color: '#6b7a99', fontSize: '0.8rem' }}>{server.transport} · {server.url || server.command}</div>
                    </div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button
                        onClick={() => openMcpEditForm(server)}
                        style={{
                          padding: '0.3rem 0.6rem',
                          borderRadius: 4,
                          border: '1px solid #1565c0',
                          background: 'transparent',
                          color: '#90caf9',
                          cursor: 'pointer',
                          fontSize: '0.8rem'
                        }}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => deleteMcpServer(server.id)}
                        style={{
                          padding: '0.3rem 0.6rem',
                          borderRadius: 4,
                          border: '1px solid #c62828',
                          background: 'transparent',
                          color: '#ef9a9a',
                          cursor: 'pointer',
                          fontSize: '0.8rem'
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}

              {mcpEditMode && (
                <div style={{
                  background: '#1a2740',
                  borderRadius: 8,
                  padding: '1rem',
                  border: '1px solid #233a5e'
                }}>
                  <h4 style={{ margin: '0 0 12px 0', color: '#42a5f5' }}>
                    {mcpEditServer ? 'Edit Server' : 'Add Server'}
                  </h4>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div>
                      <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>Server ID *</label>
                      <input
                        type="text"
                        value={mcpFormData.id}
                        onChange={e => setMcpFormData({ ...mcpFormData, id: e.target.value })}
                        disabled={!!mcpEditServer}
                        placeholder="splunk_dev"
                        style={{
                          width: '100%',
                          padding: '0.5rem',
                          borderRadius: 6,
                          border: '1px solid #233a5e',
                          background: '#102040',
                          color: 'white',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>Name</label>
                      <input
                        type="text"
                        value={mcpFormData.name}
                        onChange={e => setMcpFormData({ ...mcpFormData, name: e.target.value })}
                        placeholder="Splunk DEV"
                        style={{
                          width: '100%',
                          padding: '0.5rem',
                          borderRadius: 6,
                          border: '1px solid #233a5e',
                          background: '#102040',
                          color: 'white',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>Transport *</label>
                      <select
                        value={mcpFormData.transport}
                        onChange={e => setMcpFormData({ ...mcpFormData, transport: e.target.value })}
                        style={{
                          width: '100%',
                          padding: '0.5rem',
                          borderRadius: 6,
                          border: '1px solid #233a5e',
                          background: '#102040',
                          color: 'white',
                          boxSizing: 'border-box'
                        }}
                      >
                        <option value="http">HTTP</option>
                        <option value="stdio">stdio</option>
                      </select>
                    </div>

                    {mcpFormData.transport === 'http' && (
                      <>
                        <div>
                          <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>URL *</label>
                          <input
                            type="text"
                            value={mcpFormData.url}
                            onChange={e => setMcpFormData({ ...mcpFormData, url: e.target.value })}
                            placeholder="https://my-server.com/mcp"
                            style={{
                              width: '100%',
                              padding: '0.5rem',
                              borderRadius: 6,
                              border: '1px solid #233a5e',
                              background: '#102040',
                              color: 'white',
                              boxSizing: 'border-box'
                            }}
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>Headers (JSON)</label>
                          <textarea
                            value={mcpFormData.headers}
                            onChange={e => setMcpFormData({ ...mcpFormData, headers: e.target.value })}
                            placeholder='{"Authorization": "bw://Splunk DEV MPC/password"}'
                            rows={3}
                            style={{
                              width: '100%',
                              padding: '0.5rem',
                              borderRadius: 6,
                              border: '1px solid #233a5e',
                              background: '#102040',
                              color: 'white',
                              fontFamily: 'monospace',
                              fontSize: '0.85rem',
                              boxSizing: 'border-box'
                            }}
                          />
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <input
                            type="checkbox"
                            id="verify-ssl"
                            checked={mcpFormData.verify_ssl}
                            onChange={e => setMcpFormData({ ...mcpFormData, verify_ssl: e.target.checked })}
                            style={{
                              width: '1rem',
                              height: '1rem',
                              cursor: 'pointer'
                            }}
                          />
                          <label htmlFor="verify-ssl" style={{ fontSize: '0.8rem', color: '#90caf9', cursor: 'pointer' }}>
                            Verify SSL certificate (uncheck for self-signed certs)
                          </label>
                        </div>
                      </>
                    )}

                    {mcpFormData.transport === 'stdio' && (
                      <>
                        <div>
                          <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>Command *</label>
                          <input
                            type="text"
                            value={mcpFormData.command}
                            onChange={e => setMcpFormData({ ...mcpFormData, command: e.target.value })}
                            placeholder="python"
                            style={{
                              width: '100%',
                              padding: '0.5rem',
                              borderRadius: 6,
                              border: '1px solid #233a5e',
                              background: '#102040',
                              color: 'white',
                              boxSizing: 'border-box'
                            }}
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>Args (space-separated)</label>
                          <input
                            type="text"
                            value={mcpFormData.args}
                            onChange={e => setMcpFormData({ ...mcpFormData, args: e.target.value })}
                            placeholder="-m my_mcp_server"
                            style={{
                              width: '100%',
                              padding: '0.5rem',
                              borderRadius: 6,
                              border: '1px solid #233a5e',
                              background: '#102040',
                              color: 'white',
                              boxSizing: 'border-box'
                            }}
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>CWD</label>
                          <input
                            type="text"
                            value={mcpFormData.cwd}
                            onChange={e => setMcpFormData({ ...mcpFormData, cwd: e.target.value })}
                            placeholder="/path/to/working/dir"
                            style={{
                              width: '100%',
                              padding: '0.5rem',
                              borderRadius: 6,
                              border: '1px solid #233a5e',
                              background: '#102040',
                              color: 'white',
                              boxSizing: 'border-box'
                            }}
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: '0.8rem', color: '#90caf9', display: 'block', marginBottom: 4 }}>Env (JSON)</label>
                          <textarea
                            value={mcpFormData.env}
                            onChange={e => setMcpFormData({ ...mcpFormData, env: e.target.value })}
                            placeholder='{"MY_VAR": "value"}'
                            rows={3}
                            style={{
                              width: '100%',
                              padding: '0.5rem',
                              borderRadius: 6,
                              border: '1px solid #233a5e',
                              background: '#102040',
                              color: 'white',
                              fontFamily: 'monospace',
                              fontSize: '0.85rem',
                              boxSizing: 'border-box'
                            }}
                          />
                        </div>
                      </>
                    )}

                    <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                      <button
                        onClick={saveMcpServer}
                        style={{
                          flex: 1,
                          padding: '0.6rem 1rem',
                          borderRadius: 6,
                          border: 'none',
                          background: '#0d47a1',
                          color: 'white',
                          fontWeight: 600,
                          cursor: 'pointer'
                        }}
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setMcpEditMode(false)}
                        style={{
                          flex: 1,
                          padding: '0.6rem 1rem',
                          borderRadius: 6,
                          border: '1px solid #233a5e',
                          background: 'transparent',
                          color: '#b3d1ff',
                          fontWeight: 600,
                          cursor: 'pointer'
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>

                  <div style={{
                    marginTop: 12,
                    padding: '0.75rem',
                    background: '#0d1a2f',
                    borderRadius: 6,
                    border: '1px dashed #233a5e',
                    fontSize: '0.8rem',
                    color: '#90caf9'
                  }}>
                    <strong>Tip:</strong> Use Bitwarden references like <code style={{ background: '#102040', padding: '0.1rem 0.4rem', borderRadius: 3 }}>bw://ItemName/field</code> for secrets
                  </div>
                </div>
              )}
            </>
          )}
        </aside>
      )}
    </div>
  );
}

export default ChatApp;
