import React, { useState } from 'react';
import { FileCode, AlertCircle, CheckCircle2, ArrowRight, Loader2 } from 'lucide-react';

export default function MarkdownPasteForm({ initialMarkdown = '', onSubmit, loading, error, taskTitle }) {
  const [markdown, setMarkdown] = useState(initialMarkdown);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!markdown.trim()) return;
    onSubmit(markdown);
  };

  const handleInsertTemplate = () => {
    const defaultTemplate = `---
title: "${taskTitle || 'Practical Task'}"
---

# Introduction
Provide an introduction and theoretical overview for this practical task.

<!-- Screenshot or diagram placeholder -->
![Installation Overview](placeholder_1)

## Implementation Steps
1. First step description here.
2. Second step description here.

<!-- Screenshot of executed command or output -->
![Output Results](placeholder_2)

## Conclusion
Brief summary of completed work and outcomes.
`;
    setMarkdown(defaultTemplate);
  };

  return (
    <form onSubmit={handleSubmit} className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <FileCode className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-100 text-sm">Step 2: Paste Generated Markdown</h3>
            <p className="text-xs text-slate-400">Paste the response returned by your LLM chat below</p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleInsertTemplate}
          className="text-xs text-slate-400 hover:text-slate-200 border border-slate-700/60 rounded-md px-2.5 py-1 bg-slate-800/40 hover:bg-slate-800 transition-colors"
        >
          Insert Starter Template
        </button>
      </div>

      <div className="relative mb-3">
        <textarea
          rows={14}
          value={markdown}
          onChange={(e) => setMarkdown(e.target.value)}
          placeholder={`---\ntitle: "Practical Title"\n---\n\n# Heading\nContent...`}
          className="w-full bg-slate-950 font-mono text-xs text-slate-200 p-4 rounded-lg border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none leading-relaxed resize-y"
          spellCheck={false}
          required
        />
      </div>

      {error && (
        <div className="mb-4 p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-start gap-2.5 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-semibold">Validation Error: </span>
            {error}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="text-[11px] text-slate-400">
          Format rules: YAML frontmatter with <code className="text-indigo-400">title</code>, exactly two <code className="text-indigo-400">---</code> lines, and <code className="text-indigo-400">![alt](placeholder)</code> images.
        </div>

        <button
          type="submit"
          disabled={loading || !markdown.trim()}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white shadow-lg shadow-emerald-600/20 transition-all cursor-pointer"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Validating...</span>
            </>
          ) : (
            <>
              <span>Validate & Extract Images</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
    </form>
  );
}
