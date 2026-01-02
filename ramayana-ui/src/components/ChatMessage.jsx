import { useState } from 'react';
import Markdown from 'react-markdown';
import { User, Sparkles } from 'lucide-react';
import { clsx } from 'clsx';
import ResearchPlan from './ResearchPlan';

const KANDA_MAP = {
    '1': 'Bala Kanda',
    '2': 'Ayodhya Kanda',
    '3': 'Aranya Kanda',
    '4': 'Kishkindha Kanda',
    '5': 'Sundara Kanda',
    '6': 'Yuddha Kanda',
    '7': 'Uttara Kanda'
};

// 1. Explicit format: [[Verse: Kanda Sarga:Shloka]]
const BRACKET_CITATION_REGEX = /\[\[Verse:\s*(.+?)\]\]/gi;
// 2. Naked format: (Official Kanda) (Number):(Number)
const NAKED_CITATION_REGEX = /(Bala|Ayodhya|Aranya|Kishkindha|Sundara|Yuddha|Uttara)\s*Kanda\s*(\d+)[: ](\d+)/gi;
// 3. Sarga-only format: (Official Kanda) Sarga (Number)
const SARGA_ONLY_REGEX = /(Bala|Ayodhya|Aranya|Kishkindha|Sundara|Yuddha|Uttara)\s*Kanda\s*(?:Sarga\s*)?(\d+)(?!\s*[:\d])/gi;

export default function ChatMessage({ message, onVerseClick }) {
    const isAi = message.role === 'assistant';

    // Pre-process content to replace citations with Markdown links
    let processedContent = message.content || "";

    // First Pass: Replace bracketed ones [[Verse: ...]] with an internal marker
    // This prevents the NAKED_CITATION_REGEX from triple-parsing them.
    processedContent = processedContent.replace(
        BRACKET_CITATION_REGEX,
        (match, content) => {
            let cleanKanda = "Bala Kanda";
            let sarga = "1";
            let shloka = "1";

            const kandaList = ['Bala', 'Ayodhya', 'Aranya', 'Kishkindha', 'Sundara', 'Yuddha', 'Uttara'];
            const foundKanda = kandaList.find(k => new RegExp(k, 'i').test(content));

            if (foundKanda) {
                cleanKanda = `${foundKanda} Kanda`;
            } else {
                const kandaIndexMatch = content.match(/Kanda\s+(\d+)/i);
                if (kandaIndexMatch) {
                    cleanKanda = KANDA_MAP[kandaIndexMatch[1]] || "Bala Kanda";
                }
            }

            const allNumbers = content.match(/\d+/g) || [];
            const isIndexed = /Kanda\s+(\d+)/i.test(content);
            const dataNumbers = isIndexed ? allNumbers.slice(1) : allNumbers;

            if (dataNumbers.length >= 2) {
                sarga = dataNumbers[0];
                shloka = dataNumbers[1];
            } else if (dataNumbers.length === 1) {
                sarga = dataNumbers[0];
                shloka = "1";
            }
            return `[[CIT:${cleanKanda}|${sarga}|${shloka}]]`;
        }
    );

    // Second Pass: Replace naked ones (Only if not already inside a bracket or part of a link)
    processedContent = processedContent.replace(
        NAKED_CITATION_REGEX,
        (match, kName, sNum, vNum, offset, fullText) => {
            const prevChar = fullText[offset - 1];
            const nextChar = fullText[offset + match.length];
            if (prevChar === '[' || prevChar === '(' || nextChar === ']' || nextChar === ')') return match;

            // Hallucination Check: If a message has many :1 citations, it's a hallucination pattern
            const isSuspicious = vNum === "1" && (processedContent.match(/:1/g) || []).length > 2;
            if (isSuspicious) return match;

            const cleanKanda = `${kName} Kanda`;
            return `[[CIT:${cleanKanda}|${sNum}|${vNum}]]`;
        }
    );

    // Third Pass: Replace Sarga-only ones
    processedContent = processedContent.replace(
        SARGA_ONLY_REGEX,
        (match, kName, sNum, offset, fullText) => {
            const prevChar = fullText[offset - 1];
            const nextChar = fullText[offset + match.length];
            if (prevChar === '[' || prevChar === '(' || nextChar === ']' || nextChar === ')') return match;

            const cleanKanda = `${kName} Kanda`;
            return `[[CIT:${cleanKanda}|${sNum}|1]]`; // Default to 1 for search purposes
        }
    );

    // Final Pass: Convert all markers to Markdown links
    processedContent = processedContent.replace(
        /\[\[CIT:(.+?)\|(\d+)\|(\d+)\]\]/g,
        (match, k, s, v) => `[${k} ${s}:${v}](http://citation/${encodeURIComponent(k)}/${s}/${v})`
    );


    return (
        <div className={clsx(
            "flex gap-4 p-6 rounded-2xl transition-all duration-300",
            isAi
                ? "bg-white border border-orange-50 shadow-sm"
                : "bg-orange-50/50 border border-transparent"
        )}>
            <div className={clsx(
                "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-sm",
                isAi ? "bg-orange-600 text-white shadow-orange-200" : "bg-white text-slate-400 border border-slate-100"
            )}>
                {isAi ? <Sparkles size={20} /> : <User size={20} />}
            </div>

            <div className="flex-1 space-y-2 min-w-0">
                <div className="font-serif font-bold text-sm tracking-wide uppercase opacity-70 mb-1">
                    {isAi ? "The Digital Rishi" : "You"}
                </div>

                {/* Visual Research Plan */}
                {isAi && message.plan && (
                    <ResearchPlan
                        steps={message.plan}
                        completedIndex={message.planCompletedIndex || 0}
                        details={message.planDetails}
                    />
                )}

                <div className="prose prose-lg prose-orange max-w-none text-slate-700 leading-relaxed font-sans">
                    <Markdown
                        components={{
                            a: ({ node, href, children, ...props }) => {
                                if (href && href.startsWith('http://citation/')) {
                                    // href format: http://citation/Kanda%20Name/Sarga/Shloka
                                    const path = href.replace('http://citation/', '');
                                    const parts = path.split('/').map(decodeURIComponent);
                                    const kanda = parts[0];
                                    const sarga = parts[1];
                                    const shloka = parts[2];

                                    return (
                                        <button
                                            onClick={(e) => {
                                                e.preventDefault();
                                                e.stopPropagation();
                                                console.log("CRITICAL: Citation Clicked!", kanda, sarga, shloka);
                                                // Backup alert to confirm code execution
                                                // window.alert("Click detected for " + kanda); 
                                                onVerseClick(kanda, sarga, shloka);
                                            }}
                                            className="relative z-[1000] inline-flex items-center gap-1 mx-1 px-1.5 py-0.5 rounded-md bg-orange-100 text-orange-700 text-xs font-bold hover:bg-orange-200 transition-all border border-orange-300 cursor-pointer shadow-sm pointer-events-auto"
                                            title="Tap to read verse"
                                            type="button"
                                        >
                                            <Sparkles size={10} className="text-orange-500" />
                                            {children}
                                        </button>
                                    );
                                }
                                return <a href={href} {...props}>{children}</a>
                            }
                        }}
                    >
                        {processedContent || message.content}
                    </Markdown>
                </div>
            </div>
        </div>
    );
}
