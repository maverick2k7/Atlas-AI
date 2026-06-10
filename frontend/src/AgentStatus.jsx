const AGENT_COLOURS = {
  supervisor:  { bg: 'rgba(139,124,248,0.15)', border: 'rgba(139,124,248,0.35)', dot: '#8b7cf8', text: '#c4bcff' },
  researcher:  { bg: 'rgba(52,211,153,0.12)',  border: 'rgba(52,211,153,0.30)',  dot: '#34d399', text: '#86efcc' },
  writer:      { bg: 'rgba(96,165,250,0.12)',  border: 'rgba(96,165,250,0.30)',  dot: '#60a5fa', text: '#93c5fd' },
  scheduler:   { bg: 'rgba(251,191,36,0.12)',  border: 'rgba(251,191,36,0.30)',  dot: '#fbbf24', text: '#fcd34d' },
  summariser:  { bg: 'rgba(74,222,128,0.12)',  border: 'rgba(74,222,128,0.30)',  dot: '#4ade80', text: '#86efac' },
};

const DEFAULT = {
  bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.15)', dot: '#888', text: 'rgba(255,255,255,0.6)',
};

export default function AgentStatus({ activeAgent }) {
  if (!activeAgent) return null;

  const { bg, border, dot, text } = AGENT_COLOURS[activeAgent] ?? DEFAULT;

  return (
    <div style={{
      display:       'inline-flex',
      alignItems:    'center',
      gap:           '8px',
      background:    bg,
      border:        `1px solid ${border}`,
      color:         text,
      borderRadius:  '100px',
      padding:       '5px 14px 5px 10px',
      fontSize:      '12px',
      fontWeight:    500,
      letterSpacing: '0.01em',
    }}>
      {/* Pulsing dot */}
      <span style={{
        width:        '7px',
        height:       '7px',
        borderRadius: '50%',
        background:   dot,
        display:      'inline-block',
        animation:    'pulse-dot 1.1s ease-in-out infinite',
        flexShrink:   0,
        boxShadow:    `0 0 6px ${dot}`,
      }} />
      <span style={{ textTransform: 'capitalize' }}>{activeAgent}</span>
      <span style={{ opacity: 0.6 }}>thinking…</span>
    </div>
  );
}
