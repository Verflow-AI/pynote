import React, { useEffect, useRef, useState } from 'react';
import { INotebookTracker } from '@jupyterlab/notebook';

import { sendChat } from './api';
import { applyChanges, getActiveNotebook, snapshotCells } from './notebookOps';
import { ChatMessage, Proposal } from './types';

interface Props {
  tracker: INotebookTracker;
}

const APPLY_PHRASES = new Set(['apply', 'yes', 'y', 'do it', 'go', 'ship it']);
const DISCARD_PHRASES = new Set(['cancel', 'discard', 'no', 'n', 'stop']);

export const ChatPanel: React.FC<Props> = ({ tracker }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [pending, setPending] = useState<Proposal | null>(null);
  const [notebookPath, setNotebookPath] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const update = () => {
      const panel = getActiveNotebook(tracker);
      setNotebookPath(panel?.context?.path ?? null);
    };
    update();
    tracker.currentChanged.connect(update);
    return () => {
      tracker.currentChanged.disconnect(update);
    };
  }, [tracker]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pending, isLoading]);

  const pushMessage = (msg: ChatMessage) => {
    setMessages(prev => [...prev, msg]);
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput('');

    // Apply / discard are handled locally — don't round-trip them to Claude.
    if (pending) {
      const lower = text.toLowerCase();
      if (APPLY_PHRASES.has(lower)) {
        const panel = getActiveNotebook(tracker);
        const result = applyChanges(panel, pending.changes);
        pushMessage({ role: 'user', content: text });
        pushMessage({
          role: 'system',
          content: `Applied ${result.applied} change${result.applied === 1 ? '' : 's'}${
            result.skipped ? ` (${result.skipped} skipped — target cell missing)` : ''
          }.`
        });
        setPending(null);
        return;
      }
      if (DISCARD_PHRASES.has(lower)) {
        pushMessage({ role: 'user', content: text });
        pushMessage({ role: 'system', content: 'Discarded the pending proposal.' });
        setPending(null);
        return;
      }
      // Fallthrough: user typed a follow-up question. Drop the old pending
      // proposal — they'll get a new one if Claude proposes again.
      setPending(null);
    }

    const userMsg: ChatMessage = { role: 'user', content: text };
    const outbound = [...messages, userMsg].filter(m => m.role !== 'system');
    pushMessage(userMsg);
    setIsLoading(true);

    try {
      const panel = getActiveNotebook(tracker);
      const cells = snapshotCells(panel);
      const response = await sendChat(outbound, cells);

      pushMessage({ role: 'assistant', content: response.text });

      if (response.proposal && response.proposal.changes.length > 0) {
        setPending(response.proposal);
        pushMessage({
          role: 'system',
          content:
            `Claude proposed ${response.proposal.changes.length} change${
              response.proposal.changes.length === 1 ? '' : 's'
            }: ${response.proposal.summary}\n` +
            `Type "apply" to accept, "cancel" to discard, or just keep chatting.`
        });
      }
    } catch (err: any) {
      pushMessage({
        role: 'system',
        content: `Error: ${err?.message ?? String(err)}`
      });
    } finally {
      setIsLoading(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="pynote-root">
      <div className="pynote-header">
        <span className="pynote-brand">
          <span className="pynote-brand-py">Py</span>
          <span className="pynote-brand-note">Note</span>
        </span>
        <span className="pynote-subtitle">
          {notebookPath ?? 'No notebook open'}
        </span>
      </div>

      <div className="pynote-messages">
        {messages.length === 0 && (
          <div className="pynote-empty">
            Ask Claude about the current notebook. When it proposes code
            changes, type <code>apply</code> to accept.
          </div>
        )}
        {messages.map((m, i) => (
          <Bubble key={i} message={m} />
        ))}
        {pending && (
          <div className="pynote-proposal">
            <div className="pynote-proposal-summary">{pending.summary}</div>
            {pending.changes.map((c, i) => (
              <div key={i} className="pynote-proposal-change">
                <div className="pynote-proposal-op">
                  {c.op === 'replace'
                    ? `replace cell ${c.target_cell_id?.slice(0, 8) ?? '?'}`
                    : c.target_cell_id
                    ? `insert after cell ${c.target_cell_id.slice(0, 8)}`
                    : 'append new cell at end'}
                </div>
                <pre className="pynote-proposal-src">{c.source}</pre>
              </div>
            ))}
          </div>
        )}
        {isLoading && <div className="pynote-loading">Thinking…</div>}
        <div ref={scrollRef} />
      </div>

      <div className="pynote-input-row">
        <textarea
          className="pynote-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={
            pending
              ? 'Type "apply" to accept, or ask a follow-up…'
              : 'Ask Claude about the notebook…'
          }
          rows={3}
          disabled={isLoading}
        />
        <button
          className="pynote-send"
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
        >
          {isLoading ? '…' : 'Send'}
        </button>
      </div>
    </div>
  );
};

const Bubble: React.FC<{ message: ChatMessage }> = ({ message }) => (
  <div className={`pynote-msg pynote-msg-${message.role}`}>
    <div className="pynote-msg-role">{message.role}</div>
    <div className="pynote-msg-body">{message.content}</div>
  </div>
);
