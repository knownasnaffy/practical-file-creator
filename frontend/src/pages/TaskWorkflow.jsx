import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  MessageSquareCode,
  FileCode,
  Images,
  Sparkles,
  CheckCircle2,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../api/client';
import InstructionBlock from '../components/InstructionBlock';
import MarkdownPasteForm from '../components/MarkdownPasteForm';
import PlaceholderList from '../components/PlaceholderList';
import GeneratePanel from '../components/GeneratePanel';
import RegenerationBadge from '../components/RegenerationBadge';

export default function TaskWorkflow({ taskId, onBack }) {
  const [task, setTask] = useState(null);
  const [placeholders, setPlaceholders] = useState([]);
  const [startingPageInfo, setStartingPageInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Workflow Active Tab
  const [activeStep, setActiveStep] = useState(1);

  // Markdown Paste State
  const [validatingMarkdown, setValidatingMarkdown] = useState(false);
  const [markdownError, setMarkdownError] = useState(null);

  // Generation State
  const [generating, setGenerating] = useState(false);
  const [generationError, setGenerationError] = useState(null);
  const [generationResult, setGenerationResult] = useState(null);

  // Rendered Instruction Prompt
  const [instructionBlock, setInstructionBlock] = useState('');

  const loadWorkflowData = async () => {
    try {
      setLoading(true);
      setError(null);

      const taskData = await api.getTask(taskId);
      setTask(taskData);

      // Construct LLM prompt text
      const promptTemplate = `Generate my practical file task ${taskData.order_index}: ${taskData.title}.\n\nIt should be markdown with the title being in the frontmatter only as a title field. You can add image placeholders as for where images and be inserted, whether they be screenshots or other forms of images. Don't use --- separators between sections. The image placeholders should be in normal markdown image format. The image placeholders should have alt text that briefly describes the image (very short). The placeholders should also be accompanied by comments that makes it clear what kind of image should go in there, it can be a proper instruction like take a screenshot of this ui or something like search terms that can be used with Google image search if applicable.`;
      setInstructionBlock(promptTemplate);

      // Load Placeholders
      const phs = await api.getPlaceholders(taskId);
      setPlaceholders(phs);

      // Load Starting Page
      try {
        const spInfo = await api.getStartingPage(taskId);
        setStartingPageInfo(spInfo);
      } catch (e) {
        console.warn('Could not load starting page yet', e);
      }

      // Automatically set active step based on status
      if (taskData.status === 'drafting') {
        setActiveStep(1);
      } else if (taskData.status === 'pasted' && phs.length === 0) {
        setActiveStep(4);
      } else if (taskData.status === 'resolving_images') {
        setActiveStep(3);
      } else if (taskData.status === 'generated') {
        setActiveStep(4);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkflowData();
  }, [taskId]);

  const handleMarkdownSubmit = async (rawMarkdown) => {
    setValidatingMarkdown(true);
    setMarkdownError(null);
    try {
      const res = await api.submitMarkdown(taskId, rawMarkdown);
      setPlaceholders(res.placeholders);
      // Reload task data
      const updatedTask = await api.getTask(taskId);
      setTask(updatedTask);

      if (res.placeholder_count > 0) {
        setActiveStep(3);
      } else {
        setActiveStep(4);
      }
    } catch (err) {
      setMarkdownError(err.message);
    } finally {
      setValidatingMarkdown(false);
    }
  };

  const handleUpdatePlaceholderUrl = async (placeholderId, url) => {
    try {
      const updated = await api.updatePlaceholder(placeholderId, {
        source_value: url,
        source_type: 'search',
      });
      setPlaceholders((prev) =>
        prev.map((p) => (p.id === placeholderId ? updated : p))
      );
    } catch (err) {
      alert(`Failed to save URL: ${err.message}`);
    }
  };

  const handleUploadPlaceholderFile = async (placeholderId, file) => {
    try {
      const uploaded = await api.uploadPlaceholderImage(placeholderId, file);
      setPlaceholders((prev) =>
        prev.map((p) => (p.id === placeholderId ? { ...p, ...uploaded } : p))
      );
    } catch (err) {
      alert(`Failed to upload file: ${err.message}`);
    }
  };

  const handleRetryPlaceholder = async (placeholderId) => {
    try {
      const retried = await api.retryPlaceholder(placeholderId);
      setPlaceholders((prev) =>
        prev.map((p) => (p.id === placeholderId ? retried : p))
      );
    } catch (err) {
      alert(`Failed to reset placeholder: ${err.message}`);
    }
  };

  const handleGeneratePdf = async (startingPageOverride) => {
    setGenerating(true);
    setGenerationError(null);
    setGenerationResult(null);
    try {
      const res = await api.generatePdf(taskId, startingPageOverride);
      setGenerationResult(res);
      const updatedTask = await api.getTask(taskId);
      setTask(updatedTask);
    } catch (err) {
      setGenerationError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-400">
        <Loader2 className="w-6 h-6 animate-spin mb-3 text-indigo-400" />
        <p className="text-xs">Loading task workflow...</p>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Tasks</span>
        </button>
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs">
          Error loading task: {error}
        </div>
      </div>
    );
  }

  const steps = [
    { id: 1, label: '1. Copy Prompt', icon: MessageSquareCode, done: task.status !== 'drafting' },
    { id: 2, label: '2. Paste Markdown', icon: FileCode, done: ['pasted', 'resolving_images', 'generated'].includes(task.status) },
    { id: 3, label: '3. Resolve Images', icon: Images, done: task.status === 'generated' || (task.status === 'pasted' && placeholders.length === 0) },
    { id: 4, label: '4. Generate PDF', icon: Sparkles, done: task.status === 'generated' && !task.needs_regeneration },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Navigation */}
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Task List</span>
      </button>

      {/* Task Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 mb-6 shadow-xl backdrop-blur-sm">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 font-mono text-sm font-bold flex-shrink-0">
              #{task.order_index}
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-lg font-bold text-slate-100">{task.title}</h1>
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
                <RegenerationBadge
                  needsRegeneration={task.needs_regeneration}
                  reason={task.regeneration_reason}
                />
              </div>
              <p className="text-xs font-mono text-slate-400 mt-1">
                {task.markdown_path || 'Drafting in progress'}
              </p>
            </div>
          </div>

          {task.page_count && (
            <div className="text-right">
              <div className="text-xs text-slate-400">Page Count</div>
              <div className="text-sm font-bold text-slate-200 font-mono">{task.page_count} Pages</div>
            </div>
          )}
        </div>

        {/* Step Tabs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-6 pt-5 border-t border-slate-800/80">
          {steps.map((step) => {
            const Icon = step.icon;
            const isActive = activeStep === step.id;
            return (
              <button
                key={step.id}
                type="button"
                onClick={() => setActiveStep(step.id)}
                className={`flex items-center gap-2.5 p-3 rounded-xl text-left border transition-all cursor-pointer ${
                  isActive
                    ? 'bg-indigo-600/20 border-indigo-500/50 text-indigo-200 shadow-md shadow-indigo-500/10'
                    : 'bg-slate-950/60 border-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : step.done
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {step.done && !isActive ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-semibold truncate">{step.label}</div>
                  <div className="text-[10px] text-slate-400 capitalize">
                    {step.done ? 'Ready' : 'Pending'}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Step Content */}
      <div className="space-y-6">
        {activeStep === 1 && (
          <InstructionBlock
            instructionBlock={instructionBlock}
            onProceedToPaste={() => setActiveStep(2)}
          />
        )}

        {activeStep === 2 && (
          <MarkdownPasteForm
            onSubmit={handleMarkdownSubmit}
            loading={validatingMarkdown}
            error={markdownError}
            taskTitle={task.title}
          />
        )}

        {activeStep === 3 && (
          <PlaceholderList
            placeholders={placeholders}
            onUpdateUrl={handleUpdatePlaceholderUrl}
            onUploadFile={handleUploadPlaceholderFile}
            onRetry={handleRetryPlaceholder}
            onProceedToGenerate={() => setActiveStep(4)}
          />
        )}

        {activeStep === 4 && (
          <GeneratePanel
            task={task}
            startingPageInfo={startingPageInfo}
            onGenerate={handleGeneratePdf}
            generating={generating}
            error={generationError}
            result={generationResult}
          />
        )}
      </div>
    </div>
  );
}
