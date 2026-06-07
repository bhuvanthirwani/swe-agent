'use client';

import React, { useState, useEffect } from 'react';
import { PipelineHistoryEntry } from '@/lib/types';

interface HistoryPanelProps {
    onRestore: (entry: any) => void;
}

function timeAgo(timestamp: string): string {
    const diff = Date.now() - new Date(timestamp).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
}

export default function HistoryPanel({ onRestore }: HistoryPanelProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [entries, setEntries] = useState<any[]>([]);
    const [confirmClear, setConfirmClear] = useState(false);

    const handleOpen = async () => {
        setIsOpen(true);
        try {
            const res = await fetch('/api/sessions');
            if (res.ok) {
                const data = await res.json();
                setEntries(data);
            }
        } catch (e) {
            console.error('Failed to load history', e);
        }
    };

    const handleRemove = (id: string) => {
        // Mock remove for now
        setEntries(prev => prev.filter(e => e.id !== id));
    };

    const handleClear = () => {
        if (confirmClear) {
            setEntries([]);
            setConfirmClear(false);
        } else {
            setConfirmClear(true);
            setTimeout(() => setConfirmClear(false), 3000);
        }
    };

    if (!isOpen) {
        return (
            <button
                onClick={handleOpen}
                className="btn-secondary"
                style={{ gap: '6px', fontSize: '13px', padding: '8px 14px' }}
                title="View past pipeline runs"
            >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                </svg>
                History
            </button>
        );
    }

    return (
        <div style={{
            position: 'fixed',
            inset: 0,
            zIndex: 100,
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'flex-end',
            padding: '80px 24px 24px',
        }}>
            {/* Backdrop */}
            <div
                onClick={() => setIsOpen(false)}
                style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)' }}
            />

            {/* Panel */}
            <div style={{
                position: 'relative',
                width: '420px',
                maxHeight: '75vh',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-primary)',
                borderRadius: 'var(--radius-lg)',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: 'var(--shadow-lg)',
                animation: 'slideInRight 0.25s ease',
            }}>
                {/* Header */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '16px 20px',
                    borderBottom: '1px solid var(--border-primary)',
                    background: 'var(--bg-glass)',
                    flexShrink: 0,
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '16px' }}>🕐</span>
                        <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                            Pipeline History
                        </span>
                        <span style={{
                            fontSize: '11px',
                            padding: '2px 8px',
                            borderRadius: '20px',
                            background: 'rgba(99,102,241,0.15)',
                            color: 'var(--accent-indigo)',
                            fontFamily: 'var(--font-mono)',
                        }}>
                            {entries.length} runs
                        </span>
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                        {entries.length > 0 && (
                            <button
                                onClick={handleClear}
                                style={{
                                    padding: '4px 10px',
                                    background: confirmClear ? 'rgba(244,63,94,0.15)' : 'var(--bg-glass)',
                                    border: `1px solid ${confirmClear ? 'rgba(244,63,94,0.3)' : 'var(--border-primary)'}`,
                                    borderRadius: '6px',
                                    fontSize: '12px',
                                    color: confirmClear ? 'var(--accent-rose)' : 'var(--text-muted)',
                                    cursor: 'pointer',
                                    fontFamily: 'var(--font-sans)',
                                }}
                            >
                                {confirmClear ? 'Confirm Clear' : 'Clear All'}
                            </button>
                        )}
                        <button
                            onClick={() => setIsOpen(false)}
                            style={{
                                padding: '4px 8px',
                                background: 'var(--bg-glass)',
                                border: '1px solid var(--border-primary)',
                                borderRadius: '6px',
                                fontSize: '12px',
                                color: 'var(--text-muted)',
                                cursor: 'pointer',
                            }}
                        >✕</button>
                    </div>
                </div>

                {/* Entries */}
                <div style={{ overflowY: 'auto', flexGrow: 1, padding: '8px' }}>
                    {entries.length === 0 ? (
                        <div style={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            padding: '40px 20px',
                            color: 'var(--text-muted)',
                            gap: '10px',
                        }}>
                            <span style={{ fontSize: '36px', opacity: 0.3 }}>🕐</span>
                            <p style={{ fontSize: '13px' }}>No past runs yet.</p>
                        </div>
                    ) : (
                        entries.map(entry => (
                            <div key={entry.id} style={{
                                padding: '12px 14px',
                                borderRadius: 'var(--radius-md)',
                                border: '1px solid var(--border-primary)',
                                marginBottom: '6px',
                                background: 'var(--bg-card)',
                                transition: 'border-color 0.15s',
                                cursor: 'default',
                            }}>
                                {/* Status + time */}
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <span style={{ fontSize: '12px' }}>{entry.status === 'complete' ? '✅' : '⏳'}</span>
                                        <span style={{
                                            fontSize: '11px',
                                            fontFamily: 'var(--font-mono)',
                                            color: 'var(--text-muted)',
                                        }}>{entry.created_at ? timeAgo(entry.created_at) : 'recently'}</span>
                                    </div>
                                    <div style={{ display: 'flex', gap: '4px', alignItems: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
                                        <span>Workflow: {entry.workflow_id}</span>
                                    </div>
                                </div>

                                <button
                                    onClick={() => { onRestore(entry); setIsOpen(false); }}
                                    style={{
                                        padding: '5px 12px',
                                        background: 'rgba(99,102,241,0.1)',
                                        border: '1px solid rgba(99,102,241,0.2)',
                                        borderRadius: '6px',
                                        fontSize: '12px',
                                        color: 'var(--accent-indigo)',
                                        cursor: 'pointer',
                                        fontFamily: 'var(--font-sans)',
                                        width: '100%',
                                    }}
                                >
                                    📂 Load Session
                                </button>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
