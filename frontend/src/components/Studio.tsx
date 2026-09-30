import React, { useState } from 'react';
import { api } from '../api/client';
import { Workflow } from '../types';
import SchemaTag from './SchemaTag';
import DagVisualizer from './DagVisualizer';
import { Loader2, Play } from 'lucide-react';

interface StudioProps {
  engineMode: 'mock' | 'live';
  onCompile: (workflow: Workflow) => void;
  compiledWorkflow: Workflow | null;
  onStartRun: (runId: string) => void;
  onTabSwitch: (tab: 'execution') => void;
}

const PRESETS = [
  "Collect seed-stage AI startups in India with company name, founders, funding amount, and career page.",
  "Gather upcoming 2026 developer hackathons with dates, locations, prize pools, and registration links.",
  "Extract B2B SaaS sales leads from permitted software directories with pricing tiers and features."
];

const Studio: React.FC<StudioProps> = ({ engineMode, onCompile, compiledWorkflow, onStartRun }) => {
  const [prompt, setPrompt] = useState('');
  const [isCompiling, setIsCompiling] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCompile = async () => {
    if (!prompt.trim()) return;
    setIsCompiling(true);
    setError(null);
    try {
      const res = await api.compile(prompt, engineMode === 'mock');
      onCompile(res);
    } catch (err: any) {
      setError(err.message || 'Failed to compile workflow');
    } finally {
      setIsCompiling(false);
    }
  };

  const handleStart = async () => {
    if (!compiledWorkflow) return;
    setIsStarting(true);
    setError(null);
    try {
      const res = await api.startRun({
        workflow_id: compiledWorkflow.workflow_id,
        approved_schema: compiledWorkflow.target_schema,
        approved_dag: compiledWorkflow.execution_dag,
        use_mock: engineMode === 'mock'
      });
      onStartRun(res.run_id);
    } catch (err: any) {
      setError(err.message || 'Failed to start run');
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Design Workflow</h2>
        <p className="text-slate-400">Describe what data you want to collect and we'll generate an extraction blueprint.</p>
        
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. Find recent job postings for AI Engineers..."
          className="h-32 w-full rounded-xl border border-border bg-surface p-4 text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />

        <div className="flex flex-wrap gap-2">
          {PRESETS.map((preset, i) => (
            <button
              key={i}
              onClick={() => setPrompt(preset)}
              className="rounded-lg border border-border bg-surface px-3 py-2 text-left text-sm text-slate-300 transition-colors hover:border-indigo-500 hover:text-indigo-400"
            >
              {preset.length > 50 ? preset.slice(0, 50) + '...' : preset}
            </button>
          ))}
        </div>

        <button
          onClick={handleCompile}
          disabled={isCompiling || !prompt.trim()}
          className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
        >
          {isCompiling && <Loader2 className="h-5 w-5 animate-spin" />}
          Compile Blueprint
        </button>

        {error && <div className="text-red-500">{error}</div>}
      </div>

      {compiledWorkflow && (
        <div className="space-y-6 rounded-xl border border-border bg-surface p-6">
          <h3 className="text-xl font-bold">Extraction Blueprint</h3>
          
          <div className="space-y-4">
            <h4 className="text-lg font-medium text-slate-300">Target Schema</h4>
            <div className="flex flex-wrap gap-3">
              {compiledWorkflow.target_schema.map((field) => (
                <SchemaTag key={field.name} field={field} />
              ))}
            </div>
          </div>

          <div className="space-y-4 pt-4 border-t border-border">
            <h4 className="text-lg font-medium text-slate-300">Execution DAG</h4>
            <DagVisualizer steps={compiledWorkflow.execution_dag} />
          </div>

          <div className="flex justify-end pt-6">
            <button
              onClick={handleStart}
              disabled={isStarting}
              className="flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-500 px-8 py-3 font-bold text-white shadow-lg transition-transform hover:scale-105 disabled:opacity-50 disabled:hover:scale-100"
            >
              {isStarting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Play className="h-5 w-5" />}
              Execute Workflow
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Studio;
