import React from 'react';
import { ExtractedRecord } from '../types';
import { X, ExternalLink, ShieldCheck } from 'lucide-react';

interface ProvenanceDrawerProps {
  record: ExtractedRecord | null;
  onClose: () => void;
}

const ProvenanceDrawer: React.FC<ProvenanceDrawerProps> = ({ record, onClose }) => {
  if (!record) return null;

  return (
    <>
      <div 
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md transform overflow-y-auto bg-surface p-6 shadow-2xl transition-transform duration-300 ease-in-out border-l border-border">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-indigo-400" />
            Data Provenance
          </h2>
          <button onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-6">
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-slate-500">Source Verification</label>
            <div className="flex items-center justify-between rounded-lg bg-[#0f1117] p-3 border border-border">
              <span className="text-sm text-slate-300">Confidence Score</span>
              <span className={`px-2.5 py-1 rounded-md text-xs font-bold
                ${record.confidence_score > 0.9 ? 'bg-green-500/20 text-green-400' : 
                  record.confidence_score > 0.7 ? 'bg-amber-500/20 text-amber-400' : 
                  'bg-red-500/20 text-red-400'}`}>
                {(record.confidence_score * 100).toFixed(1)}%
              </span>
            </div>
            {record.created_at && (
              <div className="text-xs text-slate-500 text-right">
                Verified at {new Date(record.created_at).toLocaleString()}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-slate-500">Source URL</label>
            <a 
              href={record.source_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm text-indigo-400 hover:text-indigo-300 break-all bg-[#0f1117] p-3 rounded-lg border border-border"
            >
              <ExternalLink className="h-4 w-4 shrink-0" />
              {record.source_url}
            </a>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-slate-500">Extracted Context (Raw Source)</label>
            <div className="rounded-lg bg-[#0f1117] border border-border p-4">
              <blockquote className="text-sm text-slate-300 whitespace-pre-wrap font-mono text-xs border-l-2 border-indigo-500 pl-4">
                {record.source_snippet || 'No snippet available.'}
              </blockquote>
            </div>
          </div>

          <div className="space-y-2 pt-4 border-t border-border">
            <label className="text-xs font-semibold uppercase text-slate-500">Structured Data</label>
            <div className="rounded-lg bg-[#0f1117] border border-border p-4">
              <pre className="text-xs text-slate-300 overflow-x-auto">
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
