import React, { useState } from 'react';
import { Copy, Check, MessageSquareCode } from 'lucide-react';

export default function InstructionBlock({ instructionBlock, onProceedToPaste }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(instructionBlock);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <MessageSquareCode className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-100 text-sm">Step 1: LLM Prompt Block</h3>
            <p className="text-xs text-slate-400">Copy this instruction prompt directly into your LLM chat (ChatGPT, Claude, etc.)</p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
            copied
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
              : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20'
          }`}
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5" />
              <span>Copied to Clipboard!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy Prompt</span>
            </>
          )}
        </button>
      </div>

      <div className="relative">
        <pre className="w-full bg-slate-950/90 text-slate-300 font-mono text-xs p-4 rounded-lg border border-slate-800/80 overflow-x-auto whitespace-pre-wrap leading-relaxed select-all">
          {instructionBlock}
        </pre>
      </div>

      {onProceedToPaste && (
        <div className="mt-4 flex justify-end">
          <button
            type="button"
            onClick={onProceedToPaste}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            Ready to paste markdown &rarr;
          </button>
        </div>
      )}
    </div>
  );
}
