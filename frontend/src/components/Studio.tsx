import React, { useState } from 'react';
import { api } from '../api/client';
import { Workflow, FieldSpec, WorkflowSpec } from '../types';
import ReactFlowDag from './ReactFlowDag';
import {
  Loader2,
  Play,
  Plus,
  Trash2,
  Sparkles,
  ShieldAlert,
  HelpCircle,
  Sliders,
  Database,
  Globe,
  AlertCircle,
} from 'lucide-react';
import { toast } from 'sonner';

interface StudioProps {
  engineMode: 'mock' | 'live';
  onCompile: (workflow: Workflow) => void;
  compiledWorkflow: Workflow | null;
  onStartRun: (runId: string) => void;
  onTabSwitch: (tab: 'execution') => void;
}

const PRESETS = [
  {
    label: 'AI Startups in India',
    prompt: 'Collect seed-stage AI startups in India with company name, founders, funding amount, location, and careers page URL.',
  },
  {
    label: 'Remote Python Internships',
    prompt: 'Find remote Python developer internships with job title, company name, stipend, apply link, and requirements.',
  },
  {
    label: 'Open-Source ML Repos',
    prompt: 'Extract top open-source machine learning GitHub repositories with repo name, stars, primary language, license, and URL.',
  },
  {
    label: 'Recent arXiv Papers (RAG)',
    prompt: 'Collect recent arXiv research papers on retrieval augmented generation with title, authors, abstract, published date, and PDF URL.',
  },
  {
    label: 'Tech Newsletter Sponsors',
    prompt: 'Extract tech newsletters accepting paid sponsorships with newsletter name, audience size, pricing, contact email, and website.',
  },
];

const FIELD_TYPES = [
  'string',
  'number',
  'integer',
  'boolean',
  'date',
  'url',
  'email',
  'phone',
  'currency',
  'enum',
  'list',
] as const;

const Studio: React.FC<StudioProps> = ({
  engineMode,
  onCompile,
  compiledWorkflow,
  onStartRun,
  onTabSwitch,
}) => {
  const [prompt, setPrompt] = useState('');
  const [isCompiling, setIsCompiling] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [compileError, setCompileError] = useState<string | null>(null);
  const [activeWorkflowSpec, setActiveWorkflowSpec] = useState<WorkflowSpec | null>(null);

  // Editable limits
  const [limits, setLimits] = useState({
    max_pages: 30,
    max_records: 50,
    per_domain_rps: 1.0,
  });

  const handleCompile = async (textToCompile?: string) => {
    const text = textToCompile || prompt;
    if (!text.trim()) {
      toast.error('Please enter a business prompt.');
      return;
    }

    setIsCompiling(true);
    setCompileError(null);
    try {
      const res = await api.compileWorkflow(text, engineMode === 'mock');
      onCompile(res);

      if (res.spec) {
        setActiveWorkflowSpec(res.spec);
        if (res.spec.limits) {
          setLimits({
            max_pages: res.spec.limits.max_pages || 30,
            max_records: res.spec.limits.max_records || 50,
            per_domain_rps: res.spec.limits.per_domain_rps || 1.0,
          });
        }
      }
      toast.success('Extraction Blueprint compiled successfully!');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Compilation failed';
      setCompileError(msg);
      toast.error(msg);
    } finally {
      setIsCompiling(false);
    }
  };

  const handleAddField = () => {
    if (!activeWorkflowSpec) return;
    const newField: FieldSpec = {
      name: `field_${activeWorkflowSpec.fields.length + 1}`,
      label: `Field ${activeWorkflowSpec.fields.length + 1}`,
      type: 'string',
      description: 'Extracted attribute',
      required: false,
      unique_key: false,
      validators: [],
    };
    setActiveWorkflowSpec({
      ...activeWorkflowSpec,
      fields: [...activeWorkflowSpec.fields, newField],
    });
    toast.info('New schema field added.');
  };

  const handleRemoveField = (index: number) => {
    if (!activeWorkflowSpec) return;
    if (activeWorkflowSpec.fields.length <= 1) {
      toast.warning('A workflow must have at least one field.');
      return;
    }
    const updated = [...activeWorkflowSpec.fields];
    updated.splice(index, 1);
    setActiveWorkflowSpec({
      ...activeWorkflowSpec,
      fields: updated,
    });
  };

  const handleFieldChange = (index: number, key: keyof FieldSpec, value: unknown) => {
    if (!activeWorkflowSpec) return;
    const updated = [...activeWorkflowSpec.fields];
    updated[index] = { ...updated[index], [key]: value };
    setActiveWorkflowSpec({
      ...activeWorkflowSpec,
      fields: updated,
    });
  };

  const handleStart = async () => {
    if (!compiledWorkflow) return;
    setIsStarting(true);
    try {
      // Save user edited spec if modified
      if (activeWorkflowSpec) {
        await api.updateWorkflow(compiledWorkflow.workflow_id, {
          ...activeWorkflowSpec,
          limits,
        });
      }

      const res = await api.startRun(
        compiledWorkflow.workflow_id,
        activeWorkflowSpec ? activeWorkflowSpec.fields : compiledWorkflow.target_schema,
        compiledWorkflow.execution_dag,
        engineMode === 'mock',
        engineMode === 'mock' ? 'demo' : 'live'
      );

      toast.success(`Workflow execution started (Run: ${res.run_id.slice(0, 8)})`);
      onStartRun(res.run_id);
      onTabSwitch('execution');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch execution';
      toast.error(msg);
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-8 p-6 overflow-y-auto">
      {/* Prompt Studio Card */}
      <div className="space-y-4 rounded-xl border border-border bg-surface p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2 text-white">
              <Sparkles className="h-6 w-6 text-indigo-400" /> Prompt Studio
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Describe your target dataset in plain English. SchemaFlow's AI Compiler designs the optimal schema, sources, and DAG.
            </p>
          </div>
          <span className="rounded-full border border-slate-700 bg-slate-800/80 px-3 py-1 text-xs text-slate-300">
            Engine: {engineMode === 'mock' ? 'Demo Mock' : 'Live Crawl'}
          </span>
        </div>

        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. Find all seed-stage AI startups in India with founder names, funding amounts, and careers page URL..."
          className="h-32 w-full rounded-xl border border-border bg-[#0f1117] p-4 text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 text-sm leading-relaxed"
        />

        {/* Presets */}
        <div className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Recommended Presets (1-Click Replay)
          </span>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setPrompt(p.prompt);
                  handleCompile(p.prompt);
                }}
                className="rounded-lg border border-border bg-[#0f1117] px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-indigo-500 hover:text-indigo-400"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex justify-between items-center pt-2">
          <button
            onClick={() => handleCompile()}
            disabled={isCompiling || !prompt.trim()}
            className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-2.5 font-semibold text-white transition-all hover:bg-indigo-500 disabled:opacity-50 text-sm shadow-md"
          >
            {isCompiling ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Compiling Workflow...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" /> Compile Workflow Blueprint
              </>
            )}
          </button>
        </div>

        {compileError && (
          <div className="rounded-lg border border-red-800/60 bg-red-950/40 p-4 text-xs text-red-300 flex items-start gap-3 mt-3 animate-in fade-in">
            <AlertCircle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-semibold text-red-200">LLM Provider Error</div>
              <div className="text-red-300/90 leading-relaxed font-mono text-[11px]">{compileError}</div>
              <div className="text-slate-400 text-[11px] pt-1">
                Tip: You can switch to <strong className="text-amber-400">Demo Replay</strong> in the top-right header to continue offline without external API keys.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Blueprint & Schema Editor */}
      {compiledWorkflow && activeWorkflowSpec && (
        <div className="space-y-6 rounded-xl border border-border bg-surface p-6 shadow-md">
          {/* Summary Header */}
          <div className="flex items-start justify-between border-b border-border pb-4">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                Generated Blueprint
              </span>
              <h3 className="text-xl font-bold text-white mt-0.5">{activeWorkflowSpec.title}</h3>
              <p className="text-xs text-slate-400 mt-1">{activeWorkflowSpec.intent_summary}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 text-xs font-medium text-indigo-300">
                Entity: {activeWorkflowSpec.entity_type}
              </span>
            </div>
          </div>

          {/* Assumptions & Risk Notes */}
          {(activeWorkflowSpec.assumptions?.length > 0 || activeWorkflowSpec.risk_notes?.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              {activeWorkflowSpec.assumptions?.length > 0 && (
                <div className="rounded-lg border border-slate-800 bg-[#0f1117] p-3 space-y-1.5">
                  <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                    <HelpCircle className="h-3.5 w-3.5 text-blue-400" /> Key Assumptions
                  </span>
                  <ul className="list-disc pl-4 space-y-1 text-slate-400">
                    {activeWorkflowSpec.assumptions.map((a, i) => (
                      <li key={i}>{a}</li>
                    ))}
                  </ul>
                </div>
              )}
              {activeWorkflowSpec.risk_notes?.length > 0 && (
                <div className="rounded-lg border border-amber-900/40 bg-amber-950/20 p-3 space-y-1.5">
                  <span className="font-semibold text-amber-300 flex items-center gap-1.5">
                    <ShieldAlert className="h-3.5 w-3.5 text-amber-400" /> Compliance & Exclusion Notes
                  </span>
                  <ul className="list-disc pl-4 space-y-1 text-amber-200/70">
                    {activeWorkflowSpec.risk_notes.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Interactive Schema Editor */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Database className="h-4 w-4 text-indigo-400" /> Schema Editor ({activeWorkflowSpec.fields.length} fields)
                </h4>
                <p className="text-xs text-slate-400">Edit fields, types, and constraints before launching the run.</p>
              </div>
              <button
                onClick={handleAddField}
                className="flex items-center gap-1.5 rounded-lg border border-border bg-[#0f1117] px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-indigo-500 hover:text-indigo-400 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" /> Add Field
              </button>
            </div>

            <div className="overflow-x-auto rounded-lg border border-border bg-[#0f1117]">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="border-b border-border bg-slate-900/50 text-[11px] font-semibold uppercase text-slate-400">
                  <tr>
                    <th className="p-3">Field Name</th>
                    <th className="p-3">Label</th>
                    <th className="p-3">Type</th>
                    <th className="p-3 text-center">Required</th>
                    <th className="p-3 text-center">Unique Key</th>
                    <th className="p-3">Extraction Instructions</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {activeWorkflowSpec.fields.map((f, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/30">
                      <td className="p-2.5">
                        <input
                          type="text"
                          value={f.name}
                          onChange={(e) => handleFieldChange(idx, 'name', e.target.value)}
                          className="w-28 rounded border border-border bg-surface px-2 py-1 text-slate-100 text-xs focus:border-indigo-500 focus:outline-none"
                        />
                      </td>
                      <td className="p-2.5">
                        <input
                          type="text"
                          value={f.label}
                          onChange={(e) => handleFieldChange(idx, 'label', e.target.value)}
                          className="w-28 rounded border border-border bg-surface px-2 py-1 text-slate-100 text-xs focus:border-indigo-500 focus:outline-none"
                        />
                      </td>
                      <td className="p-2.5">
                        <select
                          value={f.type}
                          onChange={(e) => handleFieldChange(idx, 'type', e.target.value)}
                          className="rounded border border-border bg-surface px-2 py-1 text-slate-100 text-xs focus:border-indigo-500 focus:outline-none"
                        >
                          {FIELD_TYPES.map((t) => (
                            <option key={t} value={t}>
                              {t}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="p-2.5 text-center">
                        <input
                          type="checkbox"
                          checked={f.required}
                          onChange={(e) => handleFieldChange(idx, 'required', e.target.checked)}
                          className="rounded border-border bg-surface text-indigo-600 focus:ring-0"
                        />
                      </td>
                      <td className="p-2.5 text-center">
                        <input
                          type="checkbox"
                          checked={f.unique_key}
                          onChange={(e) => handleFieldChange(idx, 'unique_key', e.target.checked)}
                          className="rounded border-border bg-surface text-indigo-600 focus:ring-0"
                        />
                      </td>
                      <td className="p-2.5">
                        <input
                          type="text"
                          value={f.description}
                          onChange={(e) => handleFieldChange(idx, 'description', e.target.value)}
                          className="w-full min-w-[200px] rounded border border-border bg-surface px-2 py-1 text-slate-100 text-xs focus:border-indigo-500 focus:outline-none"
                        />
                      </td>
                      <td className="p-2.5 text-right">
                        <button
                          onClick={() => handleRemoveField(idx)}
                          className="text-slate-500 hover:text-red-400 p-1 transition-colors"
                          title="Delete field"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Source Strategy Plan */}
          {activeWorkflowSpec.source_strategy && (
            <div className="rounded-lg border border-slate-800 bg-[#0f1117] p-4 space-y-2">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Globe className="h-3.5 w-3.5 text-indigo-400" /> Source Strategy & Permitted Connectors
              </span>
              <p className="text-xs text-slate-400">{activeWorkflowSpec.source_strategy.rationale}</p>
              <div className="flex flex-wrap gap-2 pt-1">
                {activeWorkflowSpec.source_strategy.connectors.map((c) => (
                  <span key={c} className="rounded bg-slate-800 border border-slate-700 px-2 py-0.5 text-[11px] font-mono text-emerald-400">
                    ✓ {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Workflow Intelligence: Assumptions, Risk Notes, and Clarifying Questions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {activeWorkflowSpec.assumptions && activeWorkflowSpec.assumptions.length > 0 && (
              <div className="rounded-lg border border-slate-800 bg-[#0f1117] p-3 space-y-2">
                <span className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-indigo-400" /> Key Assumptions
                </span>
                <ul className="space-y-1 text-[11px] text-slate-400 list-disc list-inside">
                  {activeWorkflowSpec.assumptions.map((item, i) => (
                    <li key={i} className="leading-relaxed">{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {activeWorkflowSpec.risk_notes && activeWorkflowSpec.risk_notes.length > 0 && (
              <div className="rounded-lg border border-slate-800 bg-[#0f1117] p-3 space-y-2">
                <span className="text-xs font-semibold text-amber-300 flex items-center gap-1.5">
                  <ShieldAlert className="h-3.5 w-3.5 text-amber-400" /> Compliance & Exclusions
                </span>
                <ul className="space-y-1 text-[11px] text-slate-400 list-disc list-inside">
                  {activeWorkflowSpec.risk_notes.map((item, i) => (
                    <li key={i} className="leading-relaxed">{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {activeWorkflowSpec.clarifying_questions && activeWorkflowSpec.clarifying_questions.length > 0 && (
              <div className="rounded-lg border border-slate-800 bg-[#0f1117] p-3 space-y-2">
                <span className="text-xs font-semibold text-purple-300 flex items-center gap-1.5">
                  <HelpCircle className="h-3.5 w-3.5 text-purple-400" /> Clarifying Questions
                </span>
                <ul className="space-y-1 text-[11px] text-slate-400 list-disc list-inside">
                  {activeWorkflowSpec.clarifying_questions.map((item, i) => (
                    <li key={i} className="leading-relaxed">{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Execution Limits & Controls */}
          <div className="rounded-lg border border-border bg-[#0f1117] p-4 space-y-3">
            <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Sliders className="h-3.5 w-3.5 text-indigo-400" /> Execution Limits & Guardrails
            </span>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div>
                <label className="text-slate-400">Max Pages ({limits.max_pages})</label>
                <input
                  type="range"
                  min="5"
                  max="100"
                  step="5"
                  value={limits.max_pages}
                  onChange={(e) => setLimits({ ...limits, max_pages: parseInt(e.target.value) })}
                  className="w-full accent-indigo-500"
                />
              </div>
              <div>
                <label className="text-slate-400">Max Records ({limits.max_records})</label>
                <input
                  type="range"
                  min="10"
                  max="200"
                  step="10"
                  value={limits.max_records}
                  onChange={(e) => setLimits({ ...limits, max_records: parseInt(e.target.value) })}
                  className="w-full accent-indigo-500"
                />
              </div>
              <div>
                <label className="text-slate-400">Per-Domain RPS ({limits.per_domain_rps} req/s)</label>
                <input
                  type="range"
                  min="0.5"
                  max="5.0"
                  step="0.5"
                  value={limits.per_domain_rps}
                  onChange={(e) => setLimits({ ...limits, per_domain_rps: parseFloat(e.target.value) })}
                  className="w-full accent-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Execution DAG preview */}
          <div className="space-y-3 border-t border-border pt-4">
            <h4 className="text-sm font-semibold text-slate-300">Execution Pipeline (Topological DAG)</h4>
            <ReactFlowDag
              dagNodes={activeWorkflowSpec?.dag}
              steps={compiledWorkflow.execution_dag}
              interactive={true}
              height={260}
            />
          </div>

          {/* Launch Button */}
          <div className="flex justify-end pt-4 border-t border-border">
            <button
              onClick={handleStart}
              disabled={isStarting}
              className="flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 px-8 py-3 font-bold text-white shadow-lg transition-transform hover:scale-[1.02] disabled:opacity-50 text-sm"
            >
              {isStarting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Launch Pipeline Execution
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Studio;
