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
                // CRITICAL FIX: If only one number exists (e.g. "Aranya Kanda 9"), it is a Sarga Ref. 
                // Set shloka to "0" (Whole Chapter) so UI doesn't say ":1"
                shloka = "0";
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

    // Third Pass: Replace Sarga-only ones (e.g. "Bala Kanda 18")
    processedContent = processedContent.replace(
        SARGA_ONLY_REGEX,
        (match, kName, sNum, offset, fullText) => {
            const prevChar = fullText[offset - 1];
            const nextChar = fullText[offset + match.length];
            if (prevChar === '[' || prevChar === '(' || nextChar === ']' || nextChar === ')') return match;

            // Critical Check: Does this look like `18:1` or `18: 5`? If so, SKIP it here.
            // The NAKED_CITATION_REGEX should have caught it, but if not, we must ensure we don't break it.
            // If the next character is a colon, this regex shouldn't have fired due to negative lookahead, but let's be safe.
            if (nextChar === ':') return match;

            const cleanKanda = `${kName} Kanda`;
            // We use '0' as a marker for "Whole Chapter" so the UI knows not to show ":1"
            return `[[CIT:${cleanKanda}|${sNum}|0]]`;
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
                            // Premium Headers: Distinct serif styling with consistent color hierarchy
                            h1: ({ node, ...props }) => <h1 className="font-serif text-2xl font-bold text-slate-900 mt-6 mb-4 pb-2 border-b border-orange-100" {...props} />,
                            h2: ({ node, ...props }) => <h2 className="font-serif text-xl font-semibold text-slate-800 mt-5 mb-3" {...props} />,
                            h3: ({ node, ...props }) => <h3 className="font-serif text-lg font-medium text-orange-900 mt-4 mb-2 uppercase tracking-wide text-xs" {...props} />,

                            // Wisdom Blockquotes: Premium inlaid style for quotes
                            blockquote: ({ node, ...props }) => (
                                <blockquote className="border-l-4 border-orange-400 pl-4 py-2 my-6 bg-orange-50/50 rounded-r-lg italic font-serif text-slate-700 leading-loose shadow-[inset_0_0_20px_rgba(251,146,60,0.05)] text-base" {...props} />
                            ),

                            // Highlighted Keywords: Subtle orange emphasis
                            strong: ({ node, ...props }) => <strong className="font-semibold text-orange-700" {...props} />,

                            // Lists: Clean spacing with custom markers
                            ul: ({ node, ...props }) => <ul className="list-disc list-outside ml-6 space-y-2 my-4 marker:text-orange-400" {...props} />,
                            ol: ({ node, ...props }) => <ol className="list-decimal list-outside ml-6 space-y-2 my-4 marker:text-orange-600 marker:font-bold" {...props} />,
                            li: ({ node, ...props }) => <li className="pl-2" {...props} />,

                            // Separator
                            hr: ({ node, ...props }) => <hr className="my-8 border-orange-100" {...props} />,

                            // Citation Renderer
                            a: ({ node, href, children, ...props }) => {
                                if (href && href.startsWith('http://citation/')) {
                                    // href format: http://citation/Kanda%20Name/Sarga/Shloka
                                    const path = href.replace('http://citation/', '');
                                    const parts = path.split('/').map(decodeURIComponent);
                                    const kanda = parts[0];
                                    const sarga = parts[1];
                                    const shloka = parts[2];

                                    // Visual Logic: If shloka is '0', it means "Whole Chapter", so don't show the verse number
                                    const isChapterRef = shloka === '0';
                                    const label = isChapterRef ? `${kanda} ${sarga}` : `${kanda} ${sarga}:${shloka}`;

                                    return (
                                        <button
                                            onClick={(e) => {
                                                e.preventDefault();
                                                e.stopPropagation();
                                                // Prevent click for Chapter Refs
                                                if (isChapterRef) return;

                                                console.log("CRITICAL: Citation Clicked!", kanda, sarga, shloka);
                                                onVerseClick(kanda, sarga, shloka);
                                            }}
                                            className={clsx(
                                                "relative z-[1000] inline-flex items-center gap-1.5 mx-1 px-2.5 py-0.5 rounded-full text-xs font-bold transition-all border shadow-sm pointer-events-auto transform hover:-translate-y-0.5",
                                                isChapterRef
                                                    ? "bg-slate-50 text-slate-500 border-slate-200 cursor-default opacity-80" // Non-clickable style
                                                    : "bg-gradient-to-r from-orange-50 to-orange-100 text-orange-800 hover:from-orange-100 hover:to-orange-200 border-orange-200 hover:border-orange-300 hover:shadow-orange-100 cursor-pointer" // Clickable premium style
                                            )}
                                            title={isChapterRef ? "Chapter Summary" : "Tap to read verse"}
                                            type="button"
                                        >
                                            <Sparkles size={10} className={isChapterRef ? "text-slate-400" : "text-orange-500"} />
                                            {label}
                                        </button>
                                    );
                                }
                                return <a href={href} {...props} className="text-orange-600 hover:underline decoration-offset-2 font-medium">{children}</a>
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
