import { useState, useEffect, useRef } from 'react';
import { Send, Menu, Clock } from 'lucide-react';
import { useAgent } from './hooks/useAgent';
import { useHistory } from './hooks/useHistory';
import ChatMessage from './components/ChatMessage';
import ThinkingBubble from './components/ThinkingBubble';
import HistorySidebar from './components/HistorySidebar';
import VerseModal from './components/VerseModal';

function App() {
  const { messages, setMessages, sendMessage, isThinking, currentThought } = useAgent();
  const { sessions, activeSessionId, setActiveSessionId, createNewSession, updateActiveSession, deleteSession } = useHistory();
  const [input, setInput] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const scrollRef = useRef(null);

  // Verse Modal State (Unified)
  const [selectedVerse, setSelectedVerse] = useState(null);
  const [isLoadingVerse, setIsLoadingVerse] = useState(false);

  const handleVerseClick = async (kanda, sarga, shloka) => {
    setIsLoadingVerse(true);
    setSelectedVerse({ kanda, sarga, shloka }); // Open modal immediately with loading state

    try {
      console.log(`Fetching verse: ${kanda} ${sarga}:${shloka}`);
      const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const res = await fetch(`${baseUrl}/verse?kanda=${encodeURIComponent(kanda)}&sarga=${sarga}&shloka=${shloka}`);
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || res.statusText);
      }
      const data = await res.json();
      setSelectedVerse(data);
    } catch (e) {
      console.error("Verse fetch error:", e);
      setSelectedVerse(null);
      alert(`Could not load verse details: ${e.message}`);
    } finally {
      setIsLoadingVerse(false);
    }
  };

  // Sync messages to History
  useEffect(() => {
    // Only update if we have meaningful messages (more than just default greeting) or if user has engaged
    if (messages.length > 1) {
      updateActiveSession(messages);
    }
  }, [messages, updateActiveSession]);

  const handleSelectSession = (id) => {
    const session = sessions.find(s => s.id === id);
    if (session) {
      setActiveSessionId(id);
      setMessages(session.messages);
    }
  };

  const handleNewSession = () => {
    createNewSession();
    setMessages([{ role: 'assistant', content: 'Namaste! I am the Digital Rishi. Ask me about Life, Strategy, or Dharma.', thoughts: [] }]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isThinking) return;

    // Clear input immediately
    const q = input;
    setInput("");

    // Create session if none active
    if (!activeSessionId) {
      createNewSession();
    }

    // Send
    await sendMessage(q);
  };

  // Auto scroll
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentThought]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <HistorySidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        onDeleteSession={deleteSession}
      />

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 bg-white/80 backdrop-blur-md border-b border-orange-100/50 p-4 z-[2000] shadow-sm transition-all">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="p-2 hover:bg-orange-50 rounded-lg text-slate-500 hover:text-orange-600 transition-colors"
            >
              <Clock size={20} />
            </button>
            <div className="flex items-center gap-3">
              <div className="relative group">
                <div className="absolute inset-0 bg-orange-400 blur-lg opacity-20 group-hover:opacity-40 transition-opacity rounded-full"></div>
                <img src="/logo.png" alt="Digital Rishi Logo" className="w-10 h-10 object-contain relative z-10" />
              </div>
              <div>
                <h1 className="font-serif font-bold text-slate-800 text-xl tracking-tight">Ramayana - Digital Rishi</h1>
                <p className="text-xs text-orange-600 font-medium tracking-wide uppercase">Wisdom for the Digital Age</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto pt-20 pb-4">
        <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center min-h-[50vh] text-center space-y-4 opacity-60">
              <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center text-orange-500 mb-2">
                <img src="/logo.png" className="w-10 opacity-80" />
              </div>
              <h3 className="font-serif text-2xl text-slate-700">Pranam. I am the Digital Rishi.</h3>
              <p className="max-w-md text-slate-500">Ask me about leadership, ethics, relationships, or dilemmas. I will search the Ramayana for guidance.</p>
            </div>
          )}

          {messages.map((msg, i) => (
            <ChatMessage
              key={msg.id || i}
              message={msg}
              onVerseClick={handleVerseClick}
            />
          ))}

          <VerseModal
            verseData={selectedVerse}
            isLoading={isLoadingVerse}
            onClose={() => setSelectedVerse(null)}
          />

          {/* Thinking Indicator */}
          {isThinking && (
            <ThinkingBubble
              currentThought={currentThought}
              thoughts={messages[messages.length - 1]?.thoughts || []}
            />
          )}

          <div ref={scrollRef} />
        </div>
      </main>

      {/* Input Area */}
      <footer className="p-4 bg-gradient-to-t from-slate-50 via-slate-50 to-transparent pt-10">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="relative group">
            <div className="absolute inset-0 bg-orange-200 opacity-20 blur-xl group-focus-within:opacity-40 transition-opacity rounded-2xl"></div>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Navigating office politics, burnout, or big decisions? Ask me..."
              className="relative w-full pl-6 pr-16 py-4 rounded-2xl border border-orange-100 bg-white/90 backdrop-blur-sm focus:bg-white focus:border-orange-300 focus:ring-4 focus:ring-orange-100 outline-none transition-all shadow-lg shadow-orange-500/5 text-lg placeholder:text-slate-400 font-medium"
              disabled={isThinking}
            />
            <button
              type="submit"
              disabled={!input.trim() || isThinking}
              className="absolute right-3 top-3 p-2 bg-orange-600 text-white rounded-xl hover:bg-orange-700 disabled:opacity-50 disabled:hover:bg-orange-600 transition-all shadow-md hover:shadow-lg active:scale-95"
            >
              <Send size={20} className={isThinking ? "animate-pulse" : ""} />
            </button>
          </form>
          <div className="text-center mt-4 text-xs font-serif text-slate-400 tracking-wider opacity-60 hover:opacity-100 transition-opacity">
            Built on the Ancient Verses of Valmiki Ramayana | Powered by Agentic AI
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
