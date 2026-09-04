import React, { useState } from 'react';
import { BookOpen, Sparkles, Terminal } from 'lucide-react';
import PracticalFileList from './pages/PracticalFileList';
import TaskList from './pages/TaskList';
import TaskWorkflow from './pages/TaskWorkflow';

export default function App() {
  const [currentView, setCurrentView] = useState('files'); // 'files' | 'tasks' | 'workflow'
  const [selectedFileId, setSelectedFileId] = useState(null);
  const [selectedTaskId, setSelectedTaskId] = useState(null);

  const handleSelectPracticalFile = (fileId) => {
    setSelectedFileId(fileId);
    setCurrentView('tasks');
  };

  const handleSelectTask = (taskId) => {
    setSelectedTaskId(taskId);
    setCurrentView('workflow');
  };

  const handleBackToFiles = () => {
    setSelectedFileId(null);
    setSelectedTaskId(null);
    setCurrentView('files');
  };

  const handleBackToTasks = () => {
    setSelectedTaskId(null);
    setCurrentView('tasks');
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation */}
      <header className="sticky top-0 z-40 bg-[#0b0f19]/80 backdrop-blur-md border-b border-slate-800/80">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div
            onClick={handleBackToFiles}
            className="flex items-center gap-2.5 cursor-pointer group"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <span className="font-bold text-sm text-slate-100 group-hover:text-indigo-300 transition-colors">
                Practical File Generator
              </span>
              <span className="text-[10px] text-slate-500 font-mono ml-2">v2.0 MVP</span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-[11px] font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Local Engine
            </span>
          </div>
        </div>
      </header>

      {/* Main Content View */}
      <main className="flex-1">
        {currentView === 'files' && (
          <PracticalFileList onSelectPracticalFile={handleSelectPracticalFile} />
        )}

        {currentView === 'tasks' && selectedFileId && (
          <TaskList
            practicalFileId={selectedFileId}
            onBack={handleBackToFiles}
            onSelectTask={handleSelectTask}
          />
        )}

        {currentView === 'workflow' && selectedTaskId && (
          <TaskWorkflow
            taskId={selectedTaskId}
            onBack={handleBackToTasks}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-400">
        Practical File Generator MVP &bull; Local-first Pandoc/LaTeX compilation pipeline
      </footer>
    </div>
  );
}
