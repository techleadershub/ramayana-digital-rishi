import { useRef, useEffect } from 'react';
import { clsx } from 'clsx';
import { X, MessageSquare, Trash2, Plus, History } from 'lucide-react';

export default function HistorySidebar({
    isOpen,
    onClose,
    sessions,
    activeSessionId,
    onSelectSession,
    onNewSession,
    onDeleteSession
}) {
    const sidebarRef = useRef(null);

    // Close on click outside
    useEffect(() => {
        function handleClickOutside(event) {
            if (sidebarRef.current && !sidebarRef.current.contains(event.target) && isOpen) {
                onClose();
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [isOpen, onClose]);

    return (
        <>
            {/* Backdrop */}
            <div
                className={clsx(
                    "fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-[3000] transition-opacity duration-300",
                    isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
                )}
            />

            {/* Sidebar Panel */}
            <div
                ref={sidebarRef}
                className={clsx(
                    "fixed inset-y-0 left-0 w-80 bg-white/95 backdrop-blur-xl shadow-2xl z-[3001] transform transition-transform duration-300 ease-out border-r border-orange-100 flex flex-col",
                    isOpen ? "translate-x-0" : "-translate-x-full"
                )}
            >
                {/* Header */}
                <div className="p-4 border-b border-orange-100/50 flex items-center justify-between">
                    <h2 className="font-serif font-bold text-slate-700 flex items-center gap-2">
                        <History size={18} className="text-orange-500" />
                        History
                    </h2>
                    <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-full text-slate-400 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* New Chat Button */}
                <div className="p-4">
                    <button
                        onClick={() => { onNewSession(); onClose(); }}
                        className="w-full flex items-center justify-center gap-2 bg-orange-600 text-white py-3 rounded-xl hover:bg-orange-700 transition-all shadow-md shadow-orange-200 font-medium"
                    >
                        <Plus size={18} />
                        New Conversation
                    </button>
                </div>

                {/* Session List */}
                <div className="flex-1 overflow-y-auto px-2 space-y-1">
                    {sessions.length === 0 && (
                        <div className="text-center text-slate-400 text-sm mt-10 p-4 italic">
                            No past conversations found.
                        </div>
                    )}

                    {sessions.map(session => (
                        <div
                            key={session.id}
                            onClick={() => { onSelectSession(session.id); onClose(); }}
                            className={clsx(
                                "group p-3 rounded-xl cursor-pointer transition-all border border-transparent hover:border-orange-100",
                                activeSessionId === session.id
                                    ? "bg-orange-50 border-orange-200 shadow-sm"
                                    : "hover:bg-white"
                            )}
                        >
                            <div className="flex items-start gap-3">
                                <MessageSquare size={16} className={clsx(
                                    "mt-1 shrink-0",
                                    activeSessionId === session.id ? "text-orange-500" : "text-slate-300"
                                )} />

                                <div className="flex-1 min-w-0">
                                    <h4 className={clsx(
                                        "text-sm font-medium truncate pr-2",
                                        activeSessionId === session.id ? "text-slate-800" : "text-slate-600"
                                    )}>
                                        {session.title || "Untitled Chat"}
                                    </h4>
                                    <p className="text-xs text-slate-400 mt-0.5">
                                        {new Date(session.timestamp).toLocaleDateString()}
                                    </p>
                                </div>

                                <button
                                    onClick={(e) => onDeleteSession(e, session.id)}
                                    className="text-slate-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity p-1"
                                    title="Delete Chat"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-slate-100 text-xs text-slate-400 text-center font-serif">
                    Stored locally in your browser
                </div>
            </div>
        </>
    );
}
