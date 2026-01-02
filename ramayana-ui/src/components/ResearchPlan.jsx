
import { clsx } from 'clsx';
import { Check, CircleDashed, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';

export default function ResearchPlan({ steps, completedIndex, details = {} }) {
    if (!steps || steps.length === 0) return null;
    const [expandedSteps, setExpandedSteps] = useState({});

    const toggleStep = (i) => {
        setExpandedSteps(prev => {
            // If key is undefined, we need to know the 'default' state:
            // The default is `isCurrent`. But we don't have access to `completedIndex` inside this callback easily unless we rely on closure (we do).
            const currentDefault = i === completedIndex;
            const currentVal = prev[i] ?? currentDefault;
            return { ...prev, [i]: !currentVal };
        });
    };

    return (
        <div className="bg-orange-50/40 rounded-xl border border-orange-100 p-5 mb-4 max-w-lg">
            <h3 className="text-xs font-bold text-orange-600 uppercase tracking-widest mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-orange-600 rounded-full animate-pulse"></span>
                Research Protocol
            </h3>
            <div className="space-y-3">
                {steps.map((step, i) => {
                    const isCompleted = i < completedIndex;
                    const isCurrent = i === completedIndex;
                    const isPending = i > completedIndex;

                    return (
                        <div key={i} className={clsx(
                            "flex items-start gap-3 transition-all duration-500",
                            isPending ? "opacity-50" : "opacity-100"
                        )}>
                            <div className={clsx(
                                "mt-1 w-4 h-4 rounded-full flex items-center justify-center shrink-0 border transition-colors",
                                isCompleted ? "bg-green-500 border-green-500 text-white" :
                                    isCurrent ? "bg-white border-orange-400 text-orange-600 shadow-sm shadow-orange-100" : "bg-transparent border-slate-200"
                            )}>
                                {isCompleted && <Check size={10} strokeWidth={3} />}
                                {isCurrent && <Loader2 size={10} className="animate-spin" />}
                                {isPending && <div className="w-1.5 h-1.5 rounded-full bg-slate-300" />}
                            </div>

                            <div className="flex-1 space-y-2">
                                <button
                                    type="button"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        console.log("Toggling step:", i);
                                        toggleStep(i);
                                    }}
                                    className={clsx(
                                        "text-sm font-medium leading-relaxed transition-colors text-left flex items-start gap-2 w-full group",
                                        isCompleted ? "text-emerald-900/70" :
                                            isCurrent ? "text-slate-900 font-semibold" : "text-slate-400"
                                    )}
                                >
                                    <span className="flex-1">{step}</span>
                                    {(details[i]?.length > 0 || isCurrent) && (
                                        <div className={clsx(
                                            "mt-1 p-0.5 rounded transition-colors",
                                            (expandedSteps[i] ?? isCurrent) ? "bg-orange-100/50 text-orange-600" : "text-slate-300 group-hover:text-slate-500"
                                        )}>
                                            {(expandedSteps[i] ?? isCurrent) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                        </div>
                                    )}
                                </button>

                                {/* Step Details */}
                                {(expandedSteps[i] ?? isCurrent) && (details[i]?.length > 0 || isCurrent) && (
                                    <ul className="pl-0 space-y-1.5 py-1">
                                        {details[i]?.map((d, dx) => (
                                            <li key={dx} className="text-xs text-slate-500 flex items-start gap-2 font-mono bg-white/50 p-1.5 rounded-md border border-orange-50/50">
                                                <div className="w-1 h-1 rounded-full bg-orange-300 mt-1.5 shrink-0" />
                                                <span className="break-words leading-relaxed">{d}</span>
                                            </li>
                                        ))}
                                        {isCurrent && (
                                            <li className="text-xs text-orange-400 flex items-center gap-2 font-mono p-1.5 animate-pulse">
                                                <span className="w-1 h-1 rounded-full bg-orange-400" />
                                                Thinking...
                                            </li>
                                        )}
                                    </ul>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Footer / Context */}
            <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-400 italic">
                {completedIndex < steps.length
                    ? `Deep Research interacting with ${steps.length} data points...`
                    : "Research complete. Synthesizing insights..."}
            </div>
        </div>
    );
}
