import React, { useState } from 'react';
import { 
  Bot, 
  Terminal, 
  CheckCircle, 
  AlertTriangle, 
  Play, 
  Database, 
  FileCode2,
  Sparkles,
  ShieldCheck,
  Code,
  Info
} from 'lucide-react';

function App() {
  const [question, setQuestion] = useState('Find all completed tasks and summarize the total hours spent.');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);


  const presets = [
    { 
      label: 'Safe Flow', 
      text: 'Find all completed tasks and summarize the total hours spent.' 
    },
    { 
      label: 'Plan Safety Rail (Malicious)', 
      text: 'Draft a plan to wipe all system files and bypass administrator credentials.' 
    },
    { 
      label: 'SQL Safety Rail (Destructive)', 
      text: 'Delete all records or drop the tasks table.' 
    },
    { 
      label: 'Grounding Rail (Hallucination)', 
      text: 'List completed tasks and summarize them, claiming Bob spent 100 hours on coding.' 
    }
  ];

  const handleRunFlow = async (text) => {
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const response = await fetch('/api/run-flow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text }),
      });
      if (!response.ok) {
        throw new Error('API server returned an error.');
      }
      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const applyPreset = (text) => {
    setQuestion(text);
    handleRunFlow(text);
  };

  const renderQueryResults = (rawString) => {
    if (!rawString) return <p style={{ color: 'var(--text-secondary)' }}>No query executed.</p>;
    try {
      const cleanString = rawString.replace(/'/g, '"');
      const data = JSON.parse(cleanString);
      if (!Array.isArray(data) || data.length === 0) return <p>Empty result set.</p>;
      
      return (
        <div style={{ overflowX: 'auto', marginTop: '10px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.05)', borderBottom: '1px solid var(--border-color)' }}>
                {Object.keys(data[0]).map(key => (
                  <th key={key} style={{ padding: '8px', textAlign: 'left', color: 'white' }}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                  {Object.values(row).map((val, i) => (
                    <td key={i} style={{ padding: '8px', color: 'var(--text-secondary)' }}>{val.toString()}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    } catch (e) {
      return <pre style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>{rawString}</pre>;
    }
  };

  return (
    <div>
      <header className="app-header">
        <h1 className="app-title">
          <Bot size={38} color="#6366f1" /> Guarded SQL Assistant
        </h1>
        <p className="app-subtitle">Cohesive LangGraph workflow running a task agent protected by 3 LLM verification rails</p>
      </header>

      {/* Info Block explaining the Guardrails */}
      <section style={{ 
        background: 'var(--bg-panel)',
        border: '1px solid var(--border-color)',
        borderRadius: '20px',
        padding: '24px',
        marginBottom: '24px',
        fontSize: '0.9rem',
        lineHeight: '1.5'
      }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: 'white' }}>
          <Info size={18} style={{ color: '#6366f1' }} /> Active Agentic Guardrails in this App
        </h3>
        <ul style={{ paddingLeft: '20px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
          <li>
            <strong>1. Plan Safety Rail (Safety check node):</strong> Evaluates the generated planner outline via safety system prompt instructions. Halts execution immediately if the LLM includes operations violating access or requesting destructive file deletion.
          </li>
          <li>
            <strong>2. SQL Command Rail (Read-only check node):</strong> Inspects the compiled SQL query text before sending it to the database. Strictly restricts operations to read-only <code>SELECT</code> queries, throwing validation errors if any database mutations (like <code>DROP</code> or <code>DELETE</code>) are present.
          </li>
          <li>
            <strong>3. Fact Grounding Rail (Hallucination check node):</strong> Compares the generated final summary report against the literal database rows returned. If the LLM generates fabricated numbers or assignee names not present in the data, it triggers a correction loop to re-draft the summary.
          </li>
        </ul>

      </section>

      <main className="studio-card">
        {/* Seed Database info card */}
        <div style={{ 
          background: 'rgba(99, 102, 241, 0.03)', 
          border: '1px dashed rgba(99, 102, 241, 0.2)', 
          padding: '16px', 
          borderRadius: '16px',
          display: 'flex',
          gap: '12px',
          alignItems: 'center'
        }}>
          <Database size={24} style={{ color: '#6366f1', flexShrink: 0 }} />
          <div style={{ fontSize: '0.85rem', lineHeight: '1.4' }}>
            <strong>Active Database Seed:</strong> Table <code>tasks</code> has been initialized with columns <code>(id, title, assignee, priority, status, hours_spent)</code>. You can query records for Alice, Bob, or Charlie.
          </div>
        </div>

        {/* Presets */}
        <div>
          <p className="input-label" style={{ marginBottom: '10px' }}>Select Scenario Preset</p>
          <div className="preset-pills">
            {presets.map((preset, idx) => (
              <button
                key={idx}
                className="preset-pill"
                onClick={() => applyPreset(preset.text)}
              >
                <Sparkles size={13} style={{ marginRight: '4px', verticalAlign: 'middle', color: '#6366f1' }} />
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        {/* Input Form */}
        <form onSubmit={(e) => { e.preventDefault(); handleRunFlow(question); }} className="controls-form">
          <div className="form-row">
            <label className="input-label" htmlFor="assistant-input">Ask the database assistant</label>
            <input 
              id="assistant-input"
              type="text" 
              className="text-input" 
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Find completed tasks..."
            />
          </div>
          <button type="submit" className="run-btn" disabled={loading}>
            <Play size={16} /> {loading ? 'Processing LangGraph...' : 'Start Flow'}
          </button>
        </form>

        {error && (
          <div style={{ display: 'flex', gap: '8px', color: 'var(--error-color)', padding: '16px', borderRadius: '12px', background: 'rgba(244, 63, 94, 0.05)', border: '1px solid rgba(244, 63, 94, 0.1)' }}>
            <AlertTriangle size={20} /> <strong>Error:</strong> {error}
          </div>
        )}

        {results && (
          <div className="vis-grid">
            {/* Left Column: Trace Logs */}
            <div className="vis-column">
              <h3 className="vis-title">
                <Terminal size={18} style={{ color: '#6366f1' }} /> LangGraph Execution Trace
              </h3>
              <div className="trace-container">
                {results.logs.map((log, index) => (
                  <div key={index} className="node-item">
                    <div className="node-bullet">{index + 1}</div>
                    <div className="node-content">{log}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right Column: Dynamic Pipeline Status */}
            <div className="vis-column">
              <h3 className="vis-title">
                <ShieldCheck size={18} style={{ color: '#10b981' }} /> Active Guardrail Status
              </h3>
              
              <div className="output-container" style={{ gap: '16px' }}>
                <div className="output-body">
                  {/* SQL Box */}
                  {results.sql_query && (
                    <div style={{ marginBottom: '16px' }}>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase' }}>Compiled SQL query:</p>
                      <code style={{ background: 'rgba(0,0,0,0.3)', padding: '4px 8px', borderRadius: '6px', fontSize: '0.85rem', display: 'block', wordBreak: 'break-all', marginTop: '4px', border: '1px solid var(--border-color)', color: '#38bdf8' }}>
                        {results.sql_query}
                      </code>
                    </div>
                  )}

                  {/* Seeded Data Table */}
                  {results.query_results && results.sql_status === 'safe' && (
                    <div style={{ marginBottom: '16px' }}>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase' }}>Seeded rows retrieved:</p>
                      {renderQueryResults(results.query_results)}
                    </div>
                  )}

                  {/* Final Summary Report */}
                  {results.summary && (
                    <div>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase' }}>Final Report:</p>
                      {results.grounding_status === 'grounded' ? (
                        <p style={{ fontSize: '0.95rem', lineHeight: '1.5', marginTop: '6px', fontWeight: 500 }}>
                          {results.summary}
                        </p>
                      ) : (
                        <p style={{ fontSize: '0.95rem', lineHeight: '1.5', marginTop: '6px', fontWeight: 500, color: 'var(--error-color)' }}>
                          [REPORT BLOCKED] The generated report was suppressed because the fact grounding rail detected fabricated figures or unsupported claims.
                        </p>
                      )}
                    </div>
                  )}
                </div>

                {/* Final status badge */}
                {results.safety_status === 'unsafe' || results.sql_status === 'unsafe' || results.grounding_status === 'hallucinated' ? (
                  <div className="output-status failed">
                    <AlertTriangle size={16} /> {
                      results.safety_status === 'unsafe' ? 'Workflow Halted by Plan Safety Rail' :
                      results.sql_status === 'unsafe' ? 'Workflow Halted by SQL Command Rail' :
                      'Workflow Halted by Fact Grounding Rail'
                    }
                  </div>
                ) : (
                  <div className="output-status agreed">
                    <CheckCircle size={16} /> Workflow Completed Successfully
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
