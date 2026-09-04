import React, { useState, useRef } from 'react';
import {
  ExternalLink,
  Link,
  Upload,
  Clipboard,
  ClipboardPaste,
  Check,
  AlertCircle,
  Loader2,
  Image as ImageIcon,
  CheckCircle2,
  X,
} from 'lucide-react';
import { api } from '../api/client';

function dataURItoBlob(dataURI) {
  try {
    const [header, base64Data] = dataURI.split(',');
    const mimeMatch = header.match(/:(.*?);/);
    const mime = mimeMatch ? mimeMatch[1] : 'image/png';
    const binary = atob(base64Data);
    const array = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      array[i] = binary.charCodeAt(i);
    }
    return new Blob([array], { type: mime });
  } catch (err) {
    console.error('Failed to convert Data URI to Blob', err);
    return null;
  }
}

export default function PlaceholderRow({ placeholder, onUpdateUrl, onUploadFile, onRetry }) {
  const [activeTab, setActiveTab] = useState(placeholder.source_type === 'custom' ? 'raw' : 'url');
  const [urlInput, setUrlInput] = useState(placeholder.source_type === 'search' ? placeholder.source_value || '' : '');
  const [isSavingUrl, setIsSavingUrl] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [pasteNotice, setPasteNotice] = useState(null);
  const [previewBlobUrl, setPreviewBlobUrl] = useState(null);
  const [isEditingExisting, setIsEditingExisting] = useState(false);

  const urlInputRef = useRef(null);
  const pasteZoneRef = useRef(null);

  const googleSearchUrl = `https://www.google.com/search?tbm=isch&q=${encodeURIComponent(placeholder.search_query)}`;

  const showFeedback = (msg, type = 'success') => {
    setPasteNotice({ msg, type });
    setTimeout(() => setPasteNotice(null), 4000);
  };

  const uploadImageFile = async (file, label = 'Pasted image') => {
    setIsUploading(true);
    try {
      const localUrl = URL.createObjectURL(file);
      setPreviewBlobUrl(localUrl);
      await onUploadFile(placeholder.id, file);
      showFeedback(`Identified content as image (${file.type || 'image/png'}) — saved as custom screenshot!`, 'success');
      setIsEditingExisting(false);
    } catch (err) {
      showFeedback(`Upload failed: ${err.message}`, 'error');
    } finally {
      setIsUploading(false);
    }
  };

  // Universal paste handler: handles raw image files, data URIs, or standard URLs
  const handleUniversalPaste = async (e) => {
    const clipboardData = e.clipboardData;
    if (!clipboardData) return;

    // 1. Check for image files in clipboardData.items or files
    const items = clipboardData.items;
    if (items && items.length > 0) {
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          e.preventDefault();
          const file = item.getAsFile();
          if (file) {
            await uploadImageFile(file, `pasted_${Date.now()}.${file.type.split('/')[1] || 'png'}`);
            return;
          }
        }
      }
    }

    if (clipboardData.files && clipboardData.files.length > 0) {
      const file = clipboardData.files[0];
      if (file.type.startsWith('image/')) {
        e.preventDefault();
        await uploadImageFile(file, file.name);
        return;
      }
    }

    // 2. Check for base64 data URI in text
    const text = clipboardData.getData('text/plain');
    if (text && text.trim().startsWith('data:image/')) {
      e.preventDefault();
      const blob = dataURItoBlob(text.trim());
      if (blob) {
        const file = new File([blob], `pasted_${Date.now()}.${blob.type.split('/')[1] || 'png'}`, { type: blob.type });
        await uploadImageFile(file, 'pasted_data_uri.png');
        return;
      }
    }

    // 3. If pasted text is a URL, set it
    if (text && (text.trim().startsWith('http://') || text.trim().startsWith('https://'))) {
      setUrlInput(text.trim());
      showFeedback('Pasted image URL from clipboard.', 'info');
    }
  };

  const handleSaveUrl = async (e) => {
    e.preventDefault();
    if (!urlInput.trim()) return;
    setIsSavingUrl(true);
    try {
      await onUpdateUrl(placeholder.id, urlInput.trim());
      showFeedback('Image URL configured successfully.', 'success');
      setIsEditingExisting(false);
    } catch (err) {
      showFeedback(`Failed to save URL: ${err.message}`, 'error');
    } finally {
      setIsSavingUrl(false);
    }
  };

  const handleFilePickerChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await uploadImageFile(file, file.name);
  };

  // Button to read from navigator.clipboard API if supported
  const handleReadFromClipboard = async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.read) {
        const clipboardItems = await navigator.clipboard.read();
        for (const item of clipboardItems) {
          const imageType = item.types.find((t) => t.startsWith('image/'));
          if (imageType) {
            const blob = await item.getType(imageType);
            const file = new File([blob], `clipboard_${Date.now()}.${imageType.split('/')[1] || 'png'}`, {
              type: imageType,
            });
            await uploadImageFile(file, 'clipboard_image.png');
            return;
          }
        }
      }

      // Fallback: try reading text
      if (navigator.clipboard && navigator.clipboard.readText) {
        const text = await navigator.clipboard.readText();
        if (text) {
          if (text.trim().startsWith('data:image/')) {
            const blob = dataURItoBlob(text.trim());
            if (blob) {
              const file = new File([blob], `clipboard_${Date.now()}.${blob.type.split('/')[1] || 'png'}`, {
                type: blob.type,
              });
              await uploadImageFile(file, 'clipboard_data_uri.png');
              return;
            }
          } else if (text.trim().startsWith('http://') || text.trim().startsWith('https://')) {
            setUrlInput(text.trim());
            setActiveTab('url');
            showFeedback('Pasted image URL from clipboard.', 'info');
            return;
          }
        }
      }

      // If no image found or permission denied, focus input
      urlInputRef.current?.focus();
      showFeedback('Clipboard does not contain an image. Press Ctrl+V in the input to paste.', 'info');
    } catch (err) {
      // Permission prompt denied or error
      urlInputRef.current?.focus();
      showFeedback('Could not read clipboard automatically. Please press Ctrl+V to paste.', 'info');
    }
  };

  const isResolved = Boolean(placeholder.resolved_path || placeholder.source_value);
  const showResolutionForm = !isResolved || isEditingExisting;

  return (
    <div className="p-4 bg-slate-950/70 border border-slate-800/90 rounded-xl transition-all">
      {/* Top Header */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-mono text-xs font-bold flex-shrink-0 mt-0.5">
            #{placeholder.position}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-slate-100">{placeholder.search_query}</h4>
              {isResolved ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  <Check className="w-3 h-3" />
                  {placeholder.source_type === 'custom' ? 'Image Attached' : 'URL Configured'}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  Pending Image
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              assets/image-{String(placeholder.position).padStart(2, '0')}.png
            </p>
          </div>
        </div>

        <a
          href={googleSearchUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700/80 transition-colors flex-shrink-0"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          <span>Search Google Images</span>
        </a>
      </div>

      {/* Inline Feedback Banner */}
      {pasteNotice && (
        <div
          className={`mb-3 p-2.5 rounded-lg text-xs flex items-center justify-between border ${
            pasteNotice.type === 'error'
              ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
              : pasteNotice.type === 'info'
              ? 'bg-blue-500/10 text-blue-300 border-blue-500/30'
              : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
          }`}
        >
          <div className="flex items-center gap-2">
            {pasteNotice.type === 'error' ? (
              <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            ) : (
              <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
            )}
            <span>{pasteNotice.msg}</span>
          </div>
          <button
            type="button"
            onClick={() => setPasteNotice(null)}
            className="text-slate-400 hover:text-white"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Resolved State Preview Card (shown when resolved and not editing) */}
      {isResolved && !isEditingExisting && (
        <div className="p-3 bg-slate-900/90 border border-slate-800 rounded-xl flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            {placeholder.source_type === 'custom' ? (
              <div className="w-12 h-12 rounded-lg bg-slate-950 border border-slate-800 overflow-hidden flex-shrink-0 flex items-center justify-center">
                <img
                  src={previewBlobUrl || api.getPlaceholderImageUrl(placeholder.id)}
                  alt={placeholder.search_query}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
                <ImageIcon className="w-5 h-5 text-slate-500" />
              </div>
            ) : (
              <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 flex-shrink-0">
                <Link className="w-4 h-4" />
              </div>
            )}

            <div className="min-w-0">
              <div className="text-xs font-semibold text-slate-200 truncate">
                {placeholder.source_type === 'custom' ? (
                  <span>Custom Screenshot / Pasted Image</span>
                ) : (
                  <span className="font-mono">{placeholder.source_value}</span>
                )}
              </div>
              <div className="text-[11px] text-emerald-400 font-medium flex items-center gap-1 mt-0.5">
                <Check className="w-3 h-3" />
                {placeholder.source_type === 'custom'
                  ? 'Image stored locally and ready for PDF build'
                  : 'URL configured — will download during PDF generation'}
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setIsEditingExisting(true)}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors flex-shrink-0 cursor-pointer"
          >
            Change Image
          </button>
        </div>
      )}

      {/* Resolution Form (shown when pending or editing) */}
      {showResolutionForm && (
        <div className="mt-2">
          {/* Mode Selector Tabs */}
          <div className="flex items-center gap-2 mb-3 border-b border-slate-800/80 pb-2">
            <button
              type="button"
              onClick={() => setActiveTab('url')}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                activeTab === 'url'
                  ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Link className="w-3.5 h-3.5" />
              <span>Paste Image URL</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('raw')}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                activeTab === 'raw'
                  ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Clipboard className="w-3.5 h-3.5" />
              <span>Paste Raw Image</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('file')}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                activeTab === 'file'
                  ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload File</span>
            </button>
          </div>

          {/* Tab 1: Paste Image URL (Smart input with image paste auto-detection) */}
          {activeTab === 'url' && (
            <div>
              <form onSubmit={handleSaveUrl} className="flex items-center gap-2">
                <div className="relative flex-1">
                  <input
                    ref={urlInputRef}
                    type="text"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    onPaste={handleUniversalPaste}
                    placeholder="Paste image URL (https://...) or press Ctrl+V to paste copied image..."
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none pr-8"
                  />
                  {isUploading && (
                    <div className="absolute right-2.5 top-2">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleReadFromClipboard}
                  disabled={isUploading}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex-shrink-0 cursor-pointer"
                  title="Paste from system clipboard"
                >
                  <ClipboardPaste className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Paste</span>
                </button>

                <button
                  type="submit"
                  disabled={isSavingUrl || isUploading || !urlInput.trim()}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition-all flex-shrink-0 cursor-pointer"
                >
                  {isSavingUrl ? 'Saving...' : 'Set URL'}
                </button>
              </form>
              <p className="text-[11px] text-slate-400 mt-1.5 flex items-center gap-1">
                <span>💡 Tip: If you have a screenshot or image in your clipboard, press</span>
                <kbd className="px-1.5 py-0.5 bg-slate-800 rounded text-slate-200 font-mono text-[10px]">
                  Ctrl+V
                </kbd>
                <span>directly into this input. It will identify the image and use it!</span>
              </p>
            </div>
          )}

          {/* Tab 2: Paste Raw Image (Dedicated clipboard dropzone) */}
          {activeTab === 'raw' && (
            <div
              ref={pasteZoneRef}
              tabIndex={0}
              onPaste={handleUniversalPaste}
              className="border border-dashed border-indigo-500/40 hover:border-indigo-400 bg-indigo-950/20 hover:bg-indigo-950/30 rounded-xl p-5 text-center focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all cursor-pointer"
            >
              {isUploading ? (
                <div className="flex flex-col items-center justify-center py-2">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-400 mb-2" />
                  <p className="text-xs font-semibold text-indigo-300">Uploading pasted image...</p>
                </div>
              ) : (
                <>
                  <Clipboard className="w-7 h-7 mx-auto text-indigo-400 mb-2" />
                  <div className="text-xs font-semibold text-slate-200 mb-1">
                    Click here & press{' '}
                    <kbd className="px-1.5 py-0.5 bg-slate-800 rounded text-slate-200 font-mono text-[11px]">
                      Ctrl+V
                    </kbd>{' '}
                    to paste raw image or screenshot
                  </div>
                  <p className="text-[11px] text-slate-400 mb-3">
                    Works with right-click "Copy Image", Flameshot, Windows Snipping Tool, or PrtSc
                  </p>
                  <button
                    type="button"
                    onClick={handleReadFromClipboard}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 transition-all cursor-pointer"
                  >
                    <ClipboardPaste className="w-3.5 h-3.5" />
                    <span>Paste from Clipboard</span>
                  </button>
                </>
              )}
            </div>
          )}

          {/* Tab 3: Upload File (File picker) */}
          {activeTab === 'file' && (
            <div onPaste={handleUniversalPaste} tabIndex={0} className="focus:outline-none">
              <label className="flex items-center justify-center gap-2 px-4 py-3 border border-dashed border-slate-700 hover:border-slate-500 rounded-xl text-xs text-slate-300 bg-slate-900/60 hover:bg-slate-900 cursor-pointer transition-colors">
                {isUploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                    <span>Uploading file...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 text-indigo-400" />
                    <span>Click to choose image file (PNG, JPG, WebP) or press Ctrl+V</span>
                  </>
                )}
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleFilePickerChange}
                  disabled={isUploading}
                  className="hidden"
                />
              </label>
            </div>
          )}

          {isEditingExisting && (
            <div className="mt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setIsEditingExisting(false)}
                className="text-xs text-slate-400 hover:text-slate-200 cursor-pointer"
              >
                Cancel change
              </button>
            </div>
          )}
        </div>
      )}

      {/* Error / Retry Bar */}
      {placeholder.error && (
        <div className="mt-2.5 p-2 bg-rose-500/10 border border-rose-500/30 rounded text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{placeholder.error}</span>
          </div>
          {onRetry && (
            <button
              type="button"
              onClick={() => onRetry(placeholder.id)}
              className="text-xs font-semibold text-rose-300 hover:text-white underline cursor-pointer"
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}
