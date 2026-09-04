import React, { useState, useEffect } from 'react';
import {
  FileCheck2,
  FileText,
  Loader2,
  AlertOctagon,
  Download,
  ExternalLink,
  Layers,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { api } from '../api/client';

export default function GeneratePanel({ task, startingPageInfo, onGenerate, generating, error, result }) {
  const [overridePage, setOverridePage] = useState('');
  const [showFullStderr, setShowFullStderr] = useState(true);

  const defaultStartingPage = startingPageInfo?.computed_starting_page || 1;

  const handleGenerateClick = () => {
    const pageVal = overridePage ? parseInt(overridePage, 10) : defaultStartingPage;
    onGenerate(pageVal);
  };

  const pdfDownloadUrl = task ? api.getPdfDownloadUrl(task.id) : '#';

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-100 text-sm">Step 4: PDF Generation & Compilation</h3>
            <p className="text-xs text-slate-400">
              Injects page numbering into temp build copy, resolves assets, and compiles with Pandoc & LaTeX
            </p>
          </div>
        </div>
      </div>

      {/* Starting Page Settings Card */}
      <div className="p-4 bg-slate-950/70 border border-slate-800/90 rounded-xl mb-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-950/80 border border-indigo-800/60 flex items-center justify-center text-indigo-400">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-200">
                Calculated Starting Page:{' '}
                <span className="font-mono text-indigo-400 text-sm font-bold ml-1">
                  {defaultStartingPage}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">
                Cover pages: {startingPageInfo?.cover_page_count ?? 2} + Earlier completed tasks:{' '}
                {startingPageInfo?.accumulated_earlier_pages ?? 0} pages
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-400">Manual Override:</label>
            <input
              type="number"
              min="1"
              value={overridePage}
              onChange={(e) => setOverridePage(e.target.value)}
              placeholder={String(defaultStartingPage)}
              className="w-20 bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-100 font-mono text-center focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
            />
          </div>
        </div>
      </div>

      {/* Action Trigger */}
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs text-slate-400">
          Ready to build PDF using <code className="text-slate-300">eisvogel</code> LaTeX template.
        </div>

        <button
          type="button"
          onClick={handleGenerateClick}
          disabled={generating}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white shadow-lg shadow-indigo-600/20 transition-all cursor-pointer"
        >
          {generating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Compiling with Pandoc...</span>
            </>
          ) : (
            <>
              <FileCheck2 className="w-4 h-4" />
              <span>{task?.status === 'generated' ? 'Re-generate PDF' : 'Generate Task PDF'}</span>
            </>
          )}
        </button>
      </div>

      {/* Error Stderr Surfacing */}
      {error && (
        <div className="mb-4 p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-rose-300 text-xs font-semibold">
              <AlertOctagon className="w-4 h-4" />
              <span>Compilation Error (Prior PDF & database state preserved)</span>
            </div>
            <button
              type="button"
              onClick={() => setShowFullStderr(!showFullStderr)}
              className="text-xs text-rose-300 hover:text-rose-200 flex items-center gap-1"
            >
              {showFullStderr ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              <span>{showFullStderr ? 'Hide Details' : 'Show Details'}</span>
            </button>
          </div>

          {showFullStderr && (
            <pre className="bg-slate-950 p-3 rounded-lg text-[11px] font-mono text-rose-200 overflow-x-auto whitespace-pre-wrap border border-rose-500/20 max-h-60 leading-relaxed">
              {error}
            </pre>
          )}
        </div>
      )}

      {/* Generated Result Success Card */}
      {(result || task?.status === 'generated') && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-semibold text-emerald-300">PDF Successfully Compiled</div>
              <div className="text-xs text-emerald-400/80 mt-0.5">
                Total Pages: <span className="font-bold text-white">{result?.page_count || task?.page_count}</span> | Starting Page: <span className="font-bold text-white">{result?.starting_page || defaultStartingPage}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <a
              href={pdfDownloadUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>View PDF</span>
            </a>

            <a
              href={pdfDownloadUrl}
              download
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download</span>
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
