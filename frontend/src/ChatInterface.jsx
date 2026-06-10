import { useState, useEffect, useRef, useCallback } from 'react';
import AgentStatus   from './AgentStatus';
import MessageBubble from './MessageBubble';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/chat';

const SUGGESTIONS = [
  "What are the latest developments in AI agents this week?",
  "Draft a professional email asking for a deadline extension",
  "Schedule a study session for tomorrow at 3pm for 2 hours",
  "Summarise my last 5 unread emails",
];

export default function ChatInterface() {
  const [messages,    setMessages]    = useState([]);
  const [inputText,   setInputText]   = useState('');
  const [activeAgent, setActiveAgent] = useState('');
  const [isLoading,   setIsLoading]   = useState(false);
  const [wsStatus,    setWsStatus]    = useState('connecting'); // 'connecting' | 'open' | 'closed'

  const wsRef        = useRef(null);
  const sessionIdRef = useRef(crypto.randomUUID());
  const bottomRef    = useRef(null);
  const textareaRef  = useRef(null);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activeAgent]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px';
  }, [inputText]);

  // WebSocket with reconnect
  const connect = useCallback(() => {
    setWsStatus('connecting');
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setWsStatus('open');
      console.log('[WS] Connected');
    };

    ws.onmessage = (event) => {
      try {
        const chunk = JSON.parse(event.data);

        if (chunk.done) {
          // Finalize ALL streaming messages (remove cursor flag from every bubble)
          setMessages(prev =>
            prev.map(m => m.streaming ? { ...m, streaming: false } : m)
          );
          setActiveAgent('');
          setIsLoading(false);
          return;
        }

        if (chunk.error) {
          setMessages(prev => [...prev, {
            role: 'assistant', content: `⚠️ ${chunk.error}`, agent: 'system', streaming: false,
          }]);
          setActiveAgent('');
          setIsLoading(false);
          return;
        }

        // Update agent badge
        if (chunk.agent) setActiveAgent(chunk.agent);

        // Append token to streaming message
        if (chunk.token) {
          setMessages(prev => {
            const last = prev[prev.length - 1];
            // Only append if last bubble is streaming AND belongs to the same agent.
            // If the agent changed (multi-agent pipeline), seal the old bubble and
            // open a new one so each agent gets its own distinct message bubble.
            if (
              last &&
              last.streaming &&
              last.role === 'assistant' &&
              last.agent === (chunk.agent || '')
            ) {
              return [
                ...prev.slice(0, -1),
                { ...last, content: last.content + chunk.token },
              ];
            }
            // Seal any previous streaming bubble before opening a new one
            const sealed = last && last.streaming
              ? [...prev.slice(0, -1), { ...last, streaming: false }]
              : prev;
            return [...sealed, {
              role: 'assistant',
              content: chunk.token,
              agent: chunk.agent || '',
              streaming: true,
            }];
          });
        }
      } catch (err) {
        console.error('[WS] Parse error:', err);
      }
    };

    ws.onclose = () => {
      setWsStatus('closed');
      setTimeout(connect, 2500);
    };

    ws.onerror = () => setWsStatus('closed');
    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  const sendMessage = useCallback((text) => {
    const msg = (text ?? inputText).trim();
    if (!msg || isLoading) return;
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    setMessages(prev => [...prev, { role: 'user', content: msg, agent: '' }]);
    wsRef.current.send(JSON.stringify({ message: msg, session_id: sessionIdRef.current }));
    setInputText('');
    setIsLoading(true);
  }, [inputText, isLoading]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const statusDot = wsStatus === 'open' ? '#22c55e' : wsStatus === 'connecting' ? '#f59e0b' : '#ef4444';

  return (
    <div style={S.shell}>
      {/* Sidebar */}
      <aside style={S.sidebar}>
        <div style={S.logo}>
          <span style={S.logoIcon}>⚡</span>
          <span style={S.logoText}>Atlas</span>
        </div>

        <div style={S.sideSection}>
          <p style={S.sideLabel}>AGENTS</p>
          {AGENTS.map(a => (
            <div key={a.id} style={S.agentPill}>
              <span style={{ ...S.agentDot, background: a.color }} />
              <span style={S.agentName}>{a.label}</span>
              <span style={S.agentRole}>{a.role}</span>
            </div>
          ))}
        </div>

        <div style={S.sideSection}>
          <p style={S.sideLabel}>TRY THESE</p>
          {SUGGESTIONS.map((s, i) => (
            <button
              key={i}
              style={S.suggestion}
              onClick={() => sendMessage(s)}
              disabled={isLoading}
            >
              {s}
            </button>
          ))}
        </div>

        <div style={S.sideFooter}>
          <span style={{ ...S.statusDot, background: statusDot }} />
          <span style={S.statusText}>
            {wsStatus === 'open' ? 'Backend connected' : wsStatus === 'connecting' ? 'Connecting…' : 'Reconnecting…'}
          </span>
        </div>
      </aside>

      {/* Main chat */}
      <main style={S.main}>
        {/* Header */}
        <header style={S.header}>
          <div>
            <h1 style={S.headerTitle}>Chat</h1>
            <p style={S.headerSub}>Multi-agent AI · Session {sessionIdRef.current.slice(0, 8)}</p>
          </div>
          {isLoading && <div style={S.headerSpinner} />}
        </header>

        {/* Messages */}
        <div style={S.messages}>
          {messages.length === 0 ? (
            <div style={S.emptyState}>
              <div style={S.emptyIcon}>🤖</div>
              <h2 style={S.emptyTitle}>How can I help?</h2>
              <p style={S.emptySub}>
                Type a task — I'll route it to the right specialist agent automatically.
              </p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <MessageBubble key={i} role={msg.role} content={msg.content} agent={msg.agent} streaming={msg.streaming} />
            ))
          )}

          {isLoading && !activeAgent && (
            <div style={S.thinkingRow}>
              <span style={S.thinkingDot} /><span style={S.thinkingDot} /><span style={S.thinkingDot} />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Agent status bar */}
        {activeAgent && (
          <div style={S.statusBar}>
            <AgentStatus activeAgent={activeAgent} />
          </div>
        )}

        {/* Input */}
        <div style={S.inputWrap}>
          <div style={S.inputBox}>
            <textarea
              id="chat-input"
              ref={textareaRef}
              style={S.textarea}
              rows={1}
              value={inputText}
              placeholder="Type a task — research, write, schedule, summarise…"
              onChange={e => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <button
              id="send-button"
              style={{ ...S.sendBtn, opacity: isLoading || !inputText.trim() ? 0.45 : 1 }}
              onClick={() => sendMessage()}
              disabled={isLoading || !inputText.trim()}
              title="Send (Enter)"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
          <p style={S.hint}>Enter to send · Shift+Enter for new line</p>
        </div>
      </main>
    </div>
  );
}

const AGENTS = [
  { id: 'supervisor', label: 'Supervisor', role: 'Routes tasks',    color: '#8b7cf8' },
  { id: 'researcher', label: 'Researcher', role: 'Web search + RAG',color: '#34d399' },
  { id: 'writer',     label: 'Writer',     role: 'Drafts & edits',  color: '#60a5fa' },
  { id: 'scheduler',  label: 'Scheduler',  role: 'Calendar events', color: '#fbbf24' },
  { id: 'summariser', label: 'Summariser', role: 'Gmail assistant', color: '#4ade80' },
];

const S = {
  shell: {
    display: 'flex',
    width: '100vw',
    height: '100vh',
    background: '#0f0f13',
    fontFamily: "'Inter', system-ui, sans-serif",
  },

  // ── Sidebar ────────────────────────────────────────────────────────────────
  sidebar: {
    width: '260px',
    flexShrink: 0,
    background: '#16161d',
    borderRight: '1px solid rgba(255,255,255,0.06)',
    display: 'flex',
    flexDirection: 'column',
    padding: '0',
    overflow: 'hidden',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '22px 20px 20px',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
  },
  logoIcon: {
    fontSize: '22px',
  },
  logoText: {
    fontSize: '17px',
    fontWeight: 700,
    color: '#f0eee8',
    letterSpacing: '-0.03em',
  },
  sideSection: {
    padding: '20px 16px 8px',
  },
  sideLabel: {
    fontSize: '10px',
    fontWeight: 600,
    letterSpacing: '0.1em',
    color: 'rgba(255,255,255,0.3)',
    marginBottom: '10px',
  },
  agentPill: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '7px 8px',
    borderRadius: '8px',
    marginBottom: '2px',
  },
  agentDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  agentName: {
    fontSize: '13px',
    fontWeight: 500,
    color: 'rgba(255,255,255,0.85)',
    flex: 1,
  },
  agentRole: {
    fontSize: '11px',
    color: 'rgba(255,255,255,0.3)',
  },
  suggestion: {
    display: 'block',
    width: '100%',
    textAlign: 'left',
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: '8px',
    padding: '8px 10px',
    fontSize: '12px',
    color: 'rgba(255,255,255,0.55)',
    cursor: 'pointer',
    marginBottom: '6px',
    lineHeight: '1.4',
    transition: 'background 0.15s, color 0.15s',
  },
  sideFooter: {
    marginTop: 'auto',
    padding: '16px 20px',
    borderTop: '1px solid rgba(255,255,255,0.06)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  statusDot: {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  statusText: {
    fontSize: '12px',
    color: 'rgba(255,255,255,0.35)',
  },

  // ── Main ───────────────────────────────────────────────────────────────────
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    background: '#0f0f13',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '18px 28px',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
    flexShrink: 0,
  },
  headerTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#f0eee8',
    letterSpacing: '-0.02em',
  },
  headerSub: {
    fontSize: '12px',
    color: 'rgba(255,255,255,0.3)',
    marginTop: '2px',
    fontWeight: 400,
  },
  headerSpinner: {
    width: '18px',
    height: '18px',
    border: '2px solid rgba(255,255,255,0.1)',
    borderTopColor: '#8b7cf8',
    borderRadius: '50%',
    animation: 'spin 0.7s linear infinite',
  },

  // ── Messages ───────────────────────────────────────────────────────────────
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '24px 28px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  emptyState: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    padding: '60px 40px',
    margin: 'auto',
  },
  emptyIcon: {
    fontSize: '48px',
    marginBottom: '16px',
    filter: 'grayscale(0.2)',
  },
  emptyTitle: {
    fontSize: '22px',
    fontWeight: 600,
    color: 'rgba(255,255,255,0.85)',
    letterSpacing: '-0.03em',
    marginBottom: '8px',
  },
  emptySub: {
    fontSize: '14px',
    color: 'rgba(255,255,255,0.35)',
    lineHeight: '1.6',
    maxWidth: '320px',
  },
  thinkingRow: {
    display: 'flex',
    gap: '5px',
    padding: '12px 0',
    alignItems: 'center',
  },
  thinkingDot: {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    background: 'rgba(255,255,255,0.25)',
    display: 'inline-block',
    animation: 'pulse-dot 1.1s ease-in-out infinite',
  },

  // ── Status bar ─────────────────────────────────────────────────────────────
  statusBar: {
    padding: '6px 28px',
    flexShrink: 0,
  },

  // ── Input ──────────────────────────────────────────────────────────────────
  inputWrap: {
    padding: '16px 28px 20px',
    flexShrink: 0,
    borderTop: '1px solid rgba(255,255,255,0.06)',
  },
  inputBox: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: '10px',
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '14px',
    padding: '10px 10px 10px 16px',
    transition: 'border-color 0.2s',
  },
  textarea: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    resize: 'none',
    fontSize: '14px',
    lineHeight: '1.5',
    color: '#f0eee8',
    fontFamily: "'Inter', system-ui, sans-serif",
    maxHeight: '160px',
    overflowY: 'auto',
  },
  sendBtn: {
    width: '38px',
    height: '38px',
    flexShrink: 0,
    background: 'linear-gradient(135deg, #8b7cf8, #6d5ae8)',
    border: 'none',
    borderRadius: '10px',
    color: '#fff',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'opacity 0.15s, transform 0.1s',
  },
  hint: {
    fontSize: '11px',
    color: 'rgba(255,255,255,0.2)',
    textAlign: 'center',
    marginTop: '8px',
  },
};
