import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = "ramayana_sessions";

export function useHistory() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);

  // Load from storage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setSessions(JSON.parse(stored));
      }
    } catch (e) {
      console.error("Failed to load history", e);
    }
  }, []);

  // Save to storage whenever sessions change
  useEffect(() => {
    if (sessions.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    }
  }, [sessions]);

  // Create a new session (Memoized)
  const createNewSession = useCallback(() => {
    const newSession = {
      id: Date.now(),
      title: "New Conversation",
      timestamp: Date.now(),
      messages: []
    };
    setSessions(prev => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
    return newSession;
  }, []);

  // Update the ACTIVE session with new messages (Memoized)
  const updateActiveSession = useCallback((messages) => {
    if (!messages || messages.length === 0) return;

    setSessions(prev => {
        // If no active session, we should have created one. 
        // If not found, create a temporary "ghost" state or just return
        if (!activeSessionId) return prev;

        return prev.map(s => {
          if (s.id === activeSessionId) {
            // OPTIMIZATION: Check if content changed. 
            // Comparing stringified content is a quick way to avoid recursion loops.
            const currContent = JSON.stringify(s.messages);
            const nextContent = JSON.stringify(messages);
            if (currContent === nextContent) return s;

            let title = s.title;
            if (title === "New Conversation") {
               const firstUserMsg = messages.find(m => m.role === 'user');
               if (firstUserMsg) {
                 title = firstUserMsg.content.slice(0, 40) + (firstUserMsg.content.length > 40 ? "..." : "");
               }
            }
            return { ...s, messages, title, timestamp: Date.now() };
          }
          return s;
        });
    });
  }, [activeSessionId]);

  const deleteSession = useCallback((e, id) => {
    if (e) e.stopPropagation();
    setSessions(prev => prev.filter(s => s.id !== id));
    setActiveSessionId(curr => curr === id ? null : curr);
  }, []);

  return {
    sessions,
    activeSessionId,
    setActiveSessionId,
    createNewSession,
    updateActiveSession,
    deleteSession
  };
}
