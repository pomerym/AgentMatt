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
                  opacity: hoveredSessionId === s.id ? 1 : 0,
                  transition: 'opacity 0.15s ease'
                }}
              >
                ✕
              </button>
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
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkBreaks]}
                components={markdownComponents}
              >
                {msg.content}
              </ReactMarkdown>
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
        </aside>
      )}
    </div>
  );
}

export default ChatApp;
