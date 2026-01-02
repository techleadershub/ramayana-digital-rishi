import { useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, BookOpen, MessageCircle } from 'lucide-react';
import { clsx } from 'clsx';

export default function VerseModal({ verseData, onClose, isLoading }) {
    const modalRef = useRef(null);

    console.log("VerseModal Render State:", { hasData: !!verseData, isLoading });

    useEffect(() => {
        function handleClickOutside(event) {
            if (modalRef.current && !modalRef.current.contains(event.target)) {
                onClose();
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [onClose]);

    if (!verseData && !isLoading) return null;

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div
                ref={modalRef}
                className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden border-2 border-orange-200 flex flex-col max-h-[85vh]"
            >
                {/* Header */}
                <div className="bg-orange-50 px-6 py-4 border-b border-orange-100 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center text-orange-600">
                            <BookOpen size={16} />
                        </div>
                        <div>
                            <h3 className="font-serif font-bold text-slate-800 text-lg leading-none">
                                {isLoading ? "Consulting Scripts..." : `Verse ${verseData?.kanda} ${verseData?.sarga}:${verseData?.shloka}`}
                            </h3>
                            <p className="text-xs text-orange-600 font-medium uppercase tracking-wider mt-1">Valmiki Ramayana</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 rounded-full hover:bg-orange-100 text-slate-500 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="overflow-y-auto p-6 space-y-6 bg-white">
                    {isLoading ? (
                        <div className="space-y-4">
                            <div className="h-4 bg-slate-100 rounded w-3/4 animate-pulse"></div>
                            <div className="h-20 bg-slate-100 rounded animate-pulse"></div>
                            <div className="h-4 bg-slate-100 rounded w-1/2 animate-pulse"></div>
                            <p className="text-center text-slate-400 text-sm italic">Searching the eternal records...</p>
                        </div>
                    ) : (
                        <>
                            {/* Sanskrit */}
                            <div className="text-center space-y-2">
                                <p className="font-serif text-xl text-slate-900 leading-relaxed italic font-medium">
                                    "{verseData?.sanskrit}"
                                </p>
                            </div>

                            {/* Divider */}
                            <div className="flex items-center gap-4">
                                <div className="h-px bg-orange-100 flex-1"></div>
                                <div className="text-orange-300">✦</div>
                                <div className="h-px bg-orange-100 flex-1"></div>
                            </div>

                            {/* Translation */}
                            <div className="space-y-2">
                                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Translation</h4>
                                <p className="text-slate-800 leading-relaxed text-base">
                                    {verseData?.translation}
                                </p>
                            </div>

                            {/* Explanation */}
                            <div className="bg-orange-50/50 rounded-xl p-5 border border-orange-100 space-y-2">
                                <h4 className="flex items-center gap-2 text-xs font-bold text-orange-600 uppercase tracking-widest">
                                    <MessageCircle size={12} />
                                    Commentary
                                </h4>
                                <p className="text-slate-700 leading-relaxed text-sm">
                                    {verseData?.explanation}
                                </p>
                                {verseData?.speaker && (
                                    <div className="pt-2 mt-2 border-t border-orange-200/30 text-xs text-orange-500 font-bold text-right">
                                        — Spoken by {verseData.speaker}
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </div>
                <div className="p-4 bg-slate-50 border-t border-slate-100 text-center">
                    <button
                        onClick={onClose}
                        className="text-sm font-bold text-slate-500 hover:text-slate-800"
                    >
                        Close [Esc]
                    </button>
                </div>
            </div>
        </div>
    );
}
