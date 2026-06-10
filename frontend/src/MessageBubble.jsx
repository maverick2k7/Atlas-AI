const AGENT_COLOURS = {
  supervisor:  '#8b7cf8',
  researcher:  '#34d399',
  writer:      '#60a5fa',
  scheduler:   '#fbbf24',
  summariser:  '#4ade80',
};

const DEFAULT_COLOUR = 'rgba(255,255,255,0.4)';

function parseContent(content) {
  if (!content) return null;
  const trimmed = content.trim();
  if (!trimmed.startsWith('{')) return { type: 'text', value: trimmed };
  try {
    const parsed = JSON.parse(trimmed);
    // Extract the first meaningful string value from the results dict
    const firstVal = Object.values(parsed).find(v => typeof v === 'string' && v.length > 0);
    if (firstVal) return { type: 'text', value: firstVal };
    return { type: 'json', value: parsed };
  } catch {
    return { type: 'text', value: trimmed };
  }
}

export default function MessageBubble({ role, content, agent, streaming = false }) {
  const isUser     = role === 'user';
  const agentColor = AGENT_COLOURS[agent] ?? DEFAULT_COLOUR;
  const parsed     = parseContent(content);

  function renderContent() {
    if (!parsed) return null;

    if (parsed.type === 'json') {
      const text = Object.entries(parsed.value)
        .map(([k, v]) => `${k}:\n${typeof v === 'object' ? JSON.stringify(v, null, 2) : v}`)
        .join('\n\n');
      return (
        <pre style={{
          background:   'rgba(0,0,0,0.3)',
          padding:      '10px 12px',
          borderRadius: '8px',
          fontSize:     '12px',
          whiteSpace:   'pre-wrap',
          wordBreak:    'break-word',
          fontFamily:   'ui-monospace, Consolas, monospace',
          margin:       0,
          color:        'rgba(255,255,255,0.75)',
          lineHeight:   '1.6',
        }}>
          {text}
        </pre>
      );
    }

    return (
      <span style={{
        fontSize:   '14px',
        lineHeight: '1.65',
        whiteSpace: 'pre-wrap',
        wordBreak:  'break-word',
      }}>
        {parsed.value}
        {streaming && (
          <span style={{
            display:    'inline-block',
            width:      '2px',
            height:     '1em',
            background: 'rgba(255,255,255,0.7)',
            marginLeft: '2px',
            verticalAlign: 'text-bottom',
            animation:  'pulse-dot 0.8s ease-in-out infinite',
          }} />
        )}
      </span>
    );
  }

  if (isUser) {
    return (
      <div className="msg-animate" style={{
        display:      'flex',
        justifyContent: 'flex-end',
        marginBottom: '16px',
      }}>
        <div style={{
          background:   'linear-gradient(135deg, #8b7cf8, #6d5ae8)',
          borderRadius: '18px 18px 4px 18px',
          padding:      '10px 16px',
          maxWidth:     '72%',
          color:        '#fff',
          fontSize:     '14px',
          lineHeight:   '1.65',
          wordBreak:    'break-word',
          boxShadow:    '0 2px 12px rgba(139,124,248,0.25)',
        }}>
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="msg-animate" style={{
      display:       'flex',
      flexDirection: 'column',
      alignItems:    'flex-start',
      marginBottom:  '16px',
    }}>
      {/* Agent label */}
      {agent && (
        <div style={{
          display:      'flex',
          alignItems:   'center',
          gap:          '5px',
          marginBottom: '5px',
        }}>
          <span style={{
            width:        '6px',
            height:       '6px',
            borderRadius: '50%',
            background:   agentColor,
            display:      'inline-block',
            boxShadow:    `0 0 5px ${agentColor}`,
          }} />
          <span style={{
            fontSize:      '11px',
            fontWeight:    600,
            color:         agentColor,
            textTransform: 'capitalize',
            letterSpacing: '0.04em',
          }}>
            {agent}
          </span>
        </div>
      )}

      {/* Bubble */}
      <div style={{
        background:   'rgba(255,255,255,0.05)',
        border:       '1px solid rgba(255,255,255,0.08)',
        borderRadius: '4px 18px 18px 18px',
        padding:      '10px 16px',
        maxWidth:     '78%',
        color:        'rgba(255,255,255,0.85)',
        backdropFilter: 'blur(4px)',
      }}>
        {renderContent()}
      </div>
    </div>
  );
}
