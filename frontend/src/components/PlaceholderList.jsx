import React from 'react';
import { Images, CheckCircle2, ArrowRight } from 'lucide-react';
import PlaceholderRow from './PlaceholderRow';

export default function PlaceholderList({
  placeholders = [],
  onUpdateUrl,
  onUploadFile,
  onRetry,
  onProceedToGenerate,
}) {
  const resolvedCount = placeholders.filter((p) => p.resolved_path || p.source_value).length;
  const allResolved = placeholders.length > 0 && resolvedCount === placeholders.length;

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Images className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-100 text-sm">Step 3: Resolve Image Placeholders</h3>
            <p className="text-xs text-slate-400">
              {placeholders.length === 0
                ? 'No placeholders extracted in this markdown file.'
                : `${resolvedCount} of ${placeholders.length} images configured`}
            </p>
          </div>
        </div>

        {placeholders.length > 0 && (
          <div className="flex items-center gap-2">
            <div className="text-xs font-medium text-slate-300">
              Progress: <span className={allResolved ? 'text-emerald-400 font-bold' : 'text-amber-400'}>{resolvedCount}/{placeholders.length}</span>
            </div>
          </div>
        )}
      </div>

      {placeholders.length === 0 ? (
        <div className="p-6 text-center text-slate-400 text-xs border border-dashed border-slate-800 rounded-lg">
          No image placeholders detected in the markdown file. You can proceed directly to PDF generation.
        </div>
      ) : (
        <div className="space-y-3 mb-4">
          {placeholders.map((ph) => (
            <PlaceholderRow
              key={ph.id}
              placeholder={ph}
              onUpdateUrl={onUpdateUrl}
              onUploadFile={onUploadFile}
              onRetry={onRetry}
            />
          ))}
        </div>
      )}

      {onProceedToGenerate && (
        <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 mt-4">
          <p className="text-xs text-slate-400">
            {allResolved
              ? 'All image sources ready. Proceed to compile PDF.'
              : 'You can generate now (unconfigured images will be skipped or resolved on retry).'}
          </p>
          <button
            type="button"
            onClick={onProceedToGenerate}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 transition-all cursor-pointer"
          >
            <span>Proceed to PDF Generation</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
