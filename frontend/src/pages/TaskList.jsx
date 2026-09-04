import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Plus,
  FileText,
  Layers,
  ChevronUp,
  ChevronDown,
  Loader2,
  Settings2,
  ExternalLink,
  Download,
  CheckCircle2,
  AlertTriangle,
  FileCode,
} from 'lucide-react';
import { api } from '../api/client';
import RegenerationBadge from '../components/RegenerationBadge';

export default function TaskList({ practicalFileId, onBack, onSelectTask }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Cover Page Count Edit
  const [coverPages, setCoverPages] = useState(2);
  const [isEditingCover, setIsEditingCover] = useState(false);
  const [savingCover, setSavingCover] = useState(false);

  // New Task Modal
  const [showNewTaskModal, setShowNewTaskModal] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [creatingTask, setCreatingTask] = useState(false);

  const loadPracticalFile = async () => {
    try {
      setLoading(true);
      const res = await api.getPracticalFile(practicalFileId);
      setData(res);
      setCoverPages(res.practical_file.cover_page_count);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPracticalFile();
  }, [practicalFileId]);

  const handleUpdateCoverPages = async (e) => {
    e.preventDefault();
    setSavingCover(true);
    try {
      await api.updateCoverPageCount(practicalFileId, coverPages);
      setIsEditingCover(false);
      await loadPracticalFile();
    } catch (err) {
      alert(`Failed to update cover pages: ${err.message}`);
    } finally {
      setSavingCover(false);
    }
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;

    setCreatingTask(true);
    try {
      const res = await api.createTask(practicalFileId, {
        title: newTaskTitle.trim(),
      });
      setShowNewTaskModal(false);
      setNewTaskTitle('');
      // Navigate directly into task workflow
      onSelectTask(res.task.id);
    } catch (err) {
      alert(`Failed to create task: ${err.message}`);
    } finally {
      setCreatingTask(false);
    }
  };

  const handleMove = async (index, direction) => {
    if (!data || !data.tasks) return;
    const tasks = [...data.tasks];
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= tasks.length) return;

    // Swap
    const temp = tasks[index];
    tasks[index] = tasks[targetIndex];
    tasks[targetIndex] = temp;

    const taskIds = tasks.map((t) => t.id);
    try {
      const updatedTasks = await api.reorderTasks(practicalFileId, taskIds);
      setData((prev) => ({
        ...prev,
        tasks: updatedTasks,
      }));
    } catch (err) {
      alert(`Failed to reorder tasks: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-400">
        <Loader2 className="w-6 h-6 animate-spin mb-3 text-indigo-400" />
        <p className="text-xs">Loading practical file tasks...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Practical Files</span>
        </button>
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs">
          Error loading tasks: {error}
        </div>
      </div>
    );
  }

  const { practical_file: pf, tasks } = data;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Navigation */}
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Practical Files</span>
      </button>

      {/* Header Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 mb-8 shadow-xl backdrop-blur-sm">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                <FileText className="w-4 h-4" />
              </div>
              <h1 className="text-xl font-bold text-slate-100">{pf.subject_name}</h1>
            </div>
            <p className="text-xs font-mono text-slate-400 mt-1">{pf.directory_path}</p>
          </div>

          <div className="flex items-center gap-3">
            {/* Cover Page Settings */}
            {isEditingCover ? (
              <form onSubmit={handleUpdateCoverPages} className="flex items-center gap-2 bg-slate-950 p-1.5 rounded-lg border border-slate-800">
                <label className="text-[11px] text-slate-400 pl-2">Cover pages:</label>
                <input
                  type="number"
                  min="0"
                  value={coverPages}
                  onChange={(e) => setCoverPages(e.target.value)}
                  className="w-14 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs font-mono text-center text-white"
                />
                <button
                  type="submit"
                  disabled={savingCover}
                  className="px-2.5 py-1 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded cursor-pointer"
                >
                  {savingCover ? 'Saving...' : 'Save'}
                </button>
                <button
                  type="button"
                  onClick={() => setIsEditingCover(false)}
                  className="px-2 py-1 text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
              </form>
            ) : (
              <button
                type="button"
                onClick={() => setIsEditingCover(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                title="Change cover page count (will cascade needs_regeneration)"
              >
                <Settings2 className="w-3.5 h-3.5" />
                <span>Cover Pages: <strong>{pf.cover_page_count}</strong></span>
              </button>
            )}

            <button
              type="button"
              onClick={() => setShowNewTaskModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>New Task</span>
            </button>
          </div>
        </div>
      </div>

      {/* Task List */}
      <div className="space-y-3">
        {tasks.length === 0 ? (
          <div className="text-center py-16 bg-slate-900/40 border border-dashed border-slate-800 rounded-2xl p-8">
            <FileCode className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-200 mb-1">No tasks created yet</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mb-6">
              Add your first practical task to generate LLM prompt instructions and start the compilation workflow.
            </p>
            <button
              type="button"
              onClick={() => setShowNewTaskModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Create Task 1</span>
            </button>
          </div>
        ) : (
          tasks.map((task, index) => (
            <div
              key={task.id}
              className="p-4 bg-slate-900/70 hover:bg-slate-900 border border-slate-800/90 rounded-xl transition-all flex items-center justify-between gap-4"
            >
              {/* Left Details */}
              <div className="flex items-center gap-3.5 flex-1 min-w-0">
                {/* Reorder Buttons */}
                <div className="flex flex-col gap-0.5">
                  <button
                    type="button"
                    onClick={() => handleMove(index, -1)}
                    disabled={index === 0}
                    className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 disabled:opacity-20 cursor-pointer"
                    title="Move Up"
                  >
                    <ChevronUp className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMove(index, 1)}
                    disabled={index === tasks.length - 1}
                    className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 disabled:opacity-20 cursor-pointer"
                    title="Move Down"
                  >
                    <ChevronDown className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center font-mono text-xs font-bold text-slate-300 flex-shrink-0">
                  #{task.order_index}
                </div>

                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3
                      onClick={() => onSelectTask(task.id)}
                      className="font-semibold text-slate-100 hover:text-indigo-300 transition-colors cursor-pointer text-sm truncate"
                    >
                      {task.title}
                    </h3>

                    {/* Status Badge */}
                    <span
                      className={`text-[11px] font-medium px-2 py-0.5 rounded capitalize ${
                        task.status === 'generated'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                          : task.status === 'resolving_images'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                          : task.status === 'pasted'
                          ? 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {task.status.replace('_', ' ')}
                    </span>

                    {/* Regeneration Drift Badge */}
                    <RegenerationBadge
                      needsRegeneration={task.needs_regeneration}
                      reason={task.regeneration_reason}
                    />
                  </div>

                  <div className="flex items-center gap-3 text-xs text-slate-400 font-mono mt-1">
                    {task.page_count ? (
                      <span>Pages: <strong className="text-slate-200">{task.page_count}</strong></span>
                    ) : (
                      <span>Not compiled yet</span>
                    )}
                    {task.pdf_path && <span>• PDF available</span>}
                  </div>
                </div>
              </div>

              {/* Right Action */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {task.pdf_path && (
                  <a
                    href={api.getPdfDownloadUrl(task.id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                    title="View PDF"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}

                <button
                  type="button"
                  onClick={() => onSelectTask(task.id)}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600/30 hover:bg-indigo-600 text-indigo-200 hover:text-white border border-indigo-500/40 transition-all cursor-pointer"
                >
                  Workflow &rarr;
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* New Task Modal */}
      {showNewTaskModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <h2 className="text-lg font-bold text-slate-100 mb-1">Create New Practical Task</h2>
            <p className="text-xs text-slate-400 mb-5">
              Enter the task topic/title. An instruction block will be rendered for you to copy into your LLM chat.
            </p>

            <form onSubmit={handleCreateTask} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Task Title / Topic</label>
                <input
                  type="text"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  placeholder="e.g. Introduction to SQL and installation of SQL Server / Oracle"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-slate-100 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-4">
                <button
                  type="button"
                  onClick={() => setShowNewTaskModal(false)}
                  disabled={creatingTask}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingTask || !newTaskTitle.trim()}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition-all cursor-pointer"
                >
                  {creatingTask ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Creating Task...</span>
                    </>
                  ) : (
                    <span>Create & Open Workflow</span>
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
