import React, { useState, useRef, useEffect } from 'react';
import { sendChatQuery } from '../services/api';

const SAMPLE_QUESTIONS = [
  'What is the flooded area?',
  'Which villages are most affected?',
  'How many buildings are affected?',
  'Show candidate evacuation sites',
  'What is the priority ranking?',
];

export default function AiAssistant({ sessionId, pipelineResult }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Hello! I can answer questions about the flood analysis results. Run an analysis first, then ask me anything.',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendQuestion = async (question) => {
    if (!question.trim() || isLoading) return;

    const userMsg = { role: 'user', text: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendChatQuery(question, sessionId);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: response.answer,
          disclaimer: response.disclaimer,
          dataUsed: response.data_used,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: `Sorry, I could not reach the AI assistant. Make sure the backend is running. (${err.message})`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendQuestion(input);
    }
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      <div className="card-title">🤖 AI Assistant</div>

      <div className="chat-disclaimer">
        ⚠️ Assistant only describes computed results. Always verify with ground surveys.
      </div>

      {!pipelineResult && (
        <div className="info-notice" style={{ marginBottom: 8 }}>
          Run an analysis to enable contextual answers.
        </div>
      )}

      {/* Sample questions */}
      <div className="sample-questions">
        {SAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            className="sample-q"
            onClick={() => sendQuestion(q)}
            disabled={isLoading}
            title={q}
          >
            {q.length > 28 ? q.slice(0, 26) + '…' : q}
          </button>
        ))}
      </div>

      {/* Chat messages */}
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.role}`}>
            <div>{msg.text}</div>
            {msg.disclaimer && (
              <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)', marginTop: 4, fontStyle: 'italic' }}>
                {msg.disclaimer}
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="chat-message assistant" style={{ color: 'var(--text-muted)' }}>
            Thinking…
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-row">
        <input
          type="text"
          placeholder="Ask about the analysis results…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        <button onClick={() => sendQuestion(input)} disabled={isLoading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
