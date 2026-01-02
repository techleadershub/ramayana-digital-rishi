import { motion } from 'framer-motion';
import { Brain, Loader2 } from 'lucide-react';

export default function ThinkingBubble({ currentThought, thoughts }) {
    if (!currentThought && thoughts.length === 0) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl mx-auto mb-4 bg-orange-50 border border-orange-100 rounded-lg p-4"
        >
            <div className="flex items-center gap-2 text-orange-600 mb-2">
                <Brain className="w-4 h-4" />
                <span className="text-sm font-semibold uppercase tracking-wider">Reviewing Ancient Archives</span>
                <Loader2 className="w-3 h-3 animate-spin ml-auto" />
            </div>

            <div className="text-sm text-slate-600 font-mono">
                {currentThought || "Synthesizing wisdom..."}
            </div>

            {thoughts.length > 0 && (
                <div className="mt-2 pl-4 border-l-2 border-orange-200 space-y-1">
                    {thoughts.slice(-2).map((t, i) => (
                        <div key={i} className="text-xs text-slate-400 truncate">{t}</div>
                    ))}
                </div>
            )}
        </motion.div>
    );
}
