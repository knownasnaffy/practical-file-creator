import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function RegenerationBadge({ needsRegeneration, reason, className = '' }) {
  if (!needsRegeneration) return null;

  const isPageDrift = reason === 'starting page changed';

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border transition-all ${
        isPageDrift
          ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
          : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
      } ${className}`}
      title={
        isPageDrift
          ? 'An earlier task changed page count. Re-generate to update running page numbers.'
          : 'File content was modified outside the application. Re-generate to update PDF.'
      }
    >
      <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
      <span>{reason || 'Needs regeneration'}</span>
    </span>
  );
}
