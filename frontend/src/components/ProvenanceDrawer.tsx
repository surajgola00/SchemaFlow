import React, { useEffect, useState } from 'react';
import { ExtractedRecord, FieldProvenance } from '../types';
import {
  X,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  ThumbsUp,
  ThumbsDown,
  Copy,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { api } from '../api/client';
import { toast } from 'sonner';

interface ProvenanceDrawerProps {
  record: ExtractedRecord | null;
  onClose: () => void;
}

const ProvenanceDrawer: React.FC<ProvenanceDrawerProps> = ({ record, onClose }) => {
  const [provenanceList, setProvenanceList] = useState<FieldProvenance[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedField, setExpandedField] = useState<string | null>(null);
  const [feedbackSent, setFeedbackSent] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!record) {
      setProvenanceList([]);
      return;
    }

    setLoading(true);
    api.getRecordProvenance(record.id)
      .then((data) => {
        setProvenanceList(data || []);
        if (data && data.length > 0) {
          setExpandedField(data[0].field_name);
        }
      })
      .catch((err) => {
        console.error('Failed to load provenance', err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [record]);

  if (!record) return null;

  const handleFeedback = async (type: 'correct' | 'wrong' | 'duplicate') => {
    try {
      await api.submitFeedback(record.id, type);
      setFeedbackSent((prev) => ({ ...prev, [record.id]: type }));
      toast.success(`Feedback recorded: marked as ${type}`);
    } catch {
      toast.error('Failed to submit feedback.');
    }
  };

  const recordConfidence = record.confidence ?? record.confidence_score ?? 0;

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg transform overflow-y-auto bg-surface p-6 shadow-2xl transition-transform duration-300 ease-in-out border-l border-border flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border pb-4 mb-6">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-indigo-400" />
              Evidence & Provenance
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Exact source quote grounding every extracted field
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-6 flex-1 overflow-y-auto pr-1">
          {/* Record Overview Card */}
          <div className="rounded-xl border border-border bg-[#0f1117] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase text-slate-400">
                Record Confidence
              </span>
              <span
                className={`rounded-md px-2.5 py-1 text-xs font-bold font-mono ${
                  recordConfidence >= 0.9
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : recordConfidence >= 0.7
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    : 'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}
              >
                {(recordConfidence * 100).toFixed(1)}% Grounded
              </span>
            </div>

            <div className="text-xs text-slate-400 flex items-center justify-between pt-1">
              <span>Grounding status:</span>
              <span className="font-semibold text-emerald-400 uppercase tracking-wider text-[11px]">
                {record.verification_status || 'verified'}
              </span>
            </div>

            {record.corroboration_count && record.corroboration_count > 1 && (
              <div className="text-xs text-purple-300 bg-purple-950/40 border border-purple-800/50 rounded-lg p-2 flex items-center gap-2">
                <Layers className="h-4 w-4 shrink-0 text-purple-400" />
                <span>Corroborated across {record.corroboration_count} distinct sources.</span>
              </div>
            )}
          </div>

          {/* Source Link */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Primary Source URL
            </label>
            <a
              href={record.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-xs text-indigo-400 hover:text-indigo-300 break-all bg-[#0f1117] p-3 rounded-lg border border-border transition-colors group"
            >
              <ExternalLink className="h-4 w-4 shrink-0 text-slate-500 group-hover:text-indigo-400" />
              {record.source_url}
            </a>
          </div>

          {/* Per-field Evidence Cards */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Field-Level Evidence Breakdown
              </label>
              <span className="text-[11px] text-slate-500">
                {provenanceList.length} verified fields
              </span>
            </div>

            {loading ? (
              <div className="p-8 text-center text-xs text-slate-500">
                Verifying quote spans against original text...
              </div>
            ) : provenanceList.length === 0 ? (
              <div className="rounded-lg bg-[#0f1117] border border-border p-4 text-xs text-slate-400">
                <blockquote className="border-l-2 border-indigo-500 pl-3 italic text-slate-300 whitespace-pre-wrap">
                  {record.source_snippet || 'No source quote provided.'}
                </blockquote>
              </div>
            ) : (
              provenanceList.map((p) => {
                const isExpanded = expandedField === p.field_name;
                return (
                  <div
                    key={p.field_name}
                    className="rounded-xl border border-border bg-[#0f1117] overflow-hidden"
                  >
                    <button
                      onClick={() => setExpandedField(isExpanded ? null : p.field_name)}
                      className="w-full flex items-center justify-between p-3.5 text-left hover:bg-slate-800/40 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        {p.verified ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-amber-400 shrink-0" />
                        )}
                        <span className="text-xs font-semibold text-slate-200 capitalize">
                          {p.field_name.replace(/_/g, ' ')}
                        </span>
                        <span className="text-xs text-slate-400 font-mono truncate max-w-[150px]">
                          = {p.value ? `"${p.value}"` : 'null'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-mono font-semibold text-emerald-400">
                          {(p.confidence * 100).toFixed(0)}%
                        </span>
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-slate-500" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-slate-500" />
                        )}
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="border-t border-border p-3.5 bg-slate-900/60 space-y-2.5 text-xs">
                        <div>
                          <span className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">
                            Supporting Verbatim Quote
                          </span>
                          <div className="mt-1 rounded border border-slate-800 bg-[#0f1117] p-2.5 font-mono text-[11px] leading-relaxed text-slate-300">
                            {p.evidence_text ? (
                              <mark className="bg-amber-400/25 text-amber-200 px-1 py-0.5 rounded font-normal">
                                {p.evidence_text}
                              </mark>
                            ) : (
                              <span className="text-slate-500 italic">No quote captured</span>
                            )}
                          </div>
                        </div>

                        {p.evidence_start >= 0 && (
                          <div className="text-[10px] text-slate-500 font-mono">
                            Offset span: [{p.evidence_start} → {p.evidence_end}]
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* User Feedback & Correction */}
          <div className="space-y-2 border-t border-border pt-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Submit Quality Feedback
            </span>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => handleFeedback('correct')}
                className={`flex items-center justify-center gap-1.5 rounded-lg border py-2 text-xs font-medium transition-colors ${
                  feedbackSent[record.id] === 'correct'
                    ? 'border-emerald-600 bg-emerald-950/40 text-emerald-300'
                    : 'border-border bg-[#0f1117] text-slate-300 hover:border-emerald-500 hover:text-emerald-400'
                }`}
              >
                <ThumbsUp className="h-3.5 w-3.5" /> Accurate
              </button>

              <button
                onClick={() => handleFeedback('wrong')}
                className={`flex items-center justify-center gap-1.5 rounded-lg border py-2 text-xs font-medium transition-colors ${
                  feedbackSent[record.id] === 'wrong'
                    ? 'border-red-600 bg-red-950/40 text-red-300'
                    : 'border-border bg-[#0f1117] text-slate-300 hover:border-red-500 hover:text-red-400'
                }`}
              >
                <ThumbsDown className="h-3.5 w-3.5" /> Wrong Value
              </button>

              <button
                onClick={() => handleFeedback('duplicate')}
                className={`flex items-center justify-center gap-1.5 rounded-lg border py-2 text-xs font-medium transition-colors ${
                  feedbackSent[record.id] === 'duplicate'
                    ? 'border-purple-600 bg-purple-950/40 text-purple-300'
                    : 'border-border bg-[#0f1117] text-slate-300 hover:border-purple-500 hover:text-purple-400'
                }`}
              >
                <Copy className="h-3.5 w-3.5" /> Duplicate
              </button>
            </div>
          </div>

          {/* Raw JSON */}
          <div className="space-y-1.5 border-t border-border pt-4">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Raw Record JSON
            </label>
            <div className="rounded-lg bg-[#0f1117] border border-border p-3">
              <pre className="text-[11px] text-slate-300 overflow-x-auto font-mono">
                {JSON.stringify(record.data, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default ProvenanceDrawer;
