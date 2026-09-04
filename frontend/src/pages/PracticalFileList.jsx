import React, { useState, useEffect } from 'react';
import { BookOpen, FolderPlus, Folder, ArrowRight, Loader2, Plus, Sparkles } from 'lucide-react';
import { api } from '../api/client';

export default function PracticalFileList({ onSelectPracticalFile }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // New Practical File Form
  const [showModal, setShowModal] = useState(false);
  const [subjectName, setSubjectName] = useState('');
  const [directoryPath, setDirectoryPath] = useState('');
  const [coverPageCount, setCoverPageCount] = useState(2);
  const [creating, setCreating] = useState(false);

  const loadFiles = async () => {
    try {
      setLoading(true);
      const data = await api.getPracticalFiles();
      setFiles(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFiles();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!subjectName.trim() || !directoryPath.trim()) return;

    setCreating(true);
    try {
      const newFile = await api.createPracticalFile({
        subject_name: subjectName.trim(),
        directory_path: directoryPath.trim(),
        cover_page_count: parseInt(coverPageCount, 10) || 2,
      });
      setShowModal(false);
      setSubjectName('');
      setDirectoryPath('');
      setCoverPageCount(2);
      onSelectPracticalFile(newFile.id);
    } catch (err) {
      alert(`Error creating practical file: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
              <BookOpen className="w-4 h-4" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Practical Files</h1>
          </div>
          <p className="text-sm text-slate-400">
            Local workspace manager for automated markdown-to-PDF college practical files
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>New Practical File</span>
        </button>
      </div>

      {/* List */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <Loader2 className="w-6 h-6 animate-spin mb-3 text-indigo-400" />
          <p className="text-xs">Loading practical files...</p>
        </div>
      ) : error ? (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs">
          Failed to load files: {error}
        </div>
      ) : files.length === 0 ? (
        <div className="text-center py-16 bg-slate-900/40 border border-dashed border-slate-800 rounded-2xl p-8">
          <Folder className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-200 mb-1">No practical files created yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
            Get started by creating a practical file workspace with a directory path on your local disk.
          </p>
          <button
            type="button"
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-all cursor-pointer"
          >
            <FolderPlus className="w-4 h-4" />
            <span>Create First Practical File</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {files.map((file) => (
            <div
              key={file.id}
              onClick={() => onSelectPracticalFile(file.id)}
              className="p-5 bg-slate-900/70 hover:bg-slate-900 border border-slate-800/90 hover:border-indigo-500/40 rounded-xl cursor-pointer transition-all group shadow-sm hover:shadow-indigo-500/5"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors">
                    {file.subject_name}
                  </h3>
                  <p className="text-xs font-mono text-slate-400 mt-1 truncate max-w-sm" title={file.directory_path}>
                    {file.directory_path}
                  </p>
                </div>
                <div className="w-8 h-8 rounded-lg bg-slate-800 group-hover:bg-indigo-600 flex items-center justify-center text-slate-400 group-hover:text-white transition-colors">
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>

              <div className="flex items-center gap-3 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
                <span>Cover pages: <strong className="text-slate-200">{file.cover_page_count}</strong></span>
                <span>•</span>
                <span>Created: {new Date(file.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <h2 className="text-lg font-bold text-slate-100 mb-1">Create Practical File</h2>
            <p className="text-xs text-slate-400 mb-5">
              Set up a practical file workspace. SQLite will index markdown files, PDFs, and assets on disk.
            </p>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Subject Name</label>
                <input
                  type="text"
                  value={subjectName}
                  onChange={(e) => setSubjectName(e.target.value)}
                  placeholder="e.g. Database Management Systems"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-slate-100 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Local Directory Path</label>
                <input
                  type="text"
                  value={directoryPath}
                  onChange={(e) => setDirectoryPath(e.target.value)}
                  placeholder="/home/user/docs/dbms-practical"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-xs font-mono text-slate-100 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                  required
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Folder where <code className="text-slate-300">tasks/</code> and <code className="text-slate-300">assets/</code> will reside.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Cover & Index Page Count</label>
                <input
                  type="number"
                  min="0"
                  value={coverPageCount}
                  onChange={(e) => setCoverPageCount(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-slate-100 font-mono focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                  required
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Default is 2 (Cover page + Table of contents). Used in starting page formula.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  disabled={creating}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !subjectName.trim() || !directoryPath.trim()}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition-all cursor-pointer"
                >
                  {creating ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Creating...</span>
                    </>
                  ) : (
                    <span>Create File Workspace</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
