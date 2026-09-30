import React from 'react';
import { DagStep } from '../types';
import { Check, Loader2, X } from 'lucide-react';

const DagVisualizer: React.FC<{ steps: DagStep[] }> = ({ steps }) => {
  return (
    <div className="flex w-full items-center justify-between overflow-x-auto py-4 scrollbar-hide">
      {steps.map((step, idx) => {
        const isLast = idx === steps.length - 1;
        let colorClass = 'bg-surface border-slate-700 text-slate-400';
        let Icon = null;
        
        if (step.status === 'completed') {
          colorClass = 'bg-green-500/20 border-green-500 text-green-400';
          Icon = <Check className="h-5 w-5" />;
        } else if (step.status === 'running') {
          colorClass = 'bg-indigo-500/20 border-indigo-500 text-indigo-400 ring-2 ring-indigo-500/50 ring-offset-2 ring-offset-[#0f1117] animate-pulse';
          Icon = <Loader2 className="h-5 w-5 animate-spin" />;
        } else if (step.status === 'failed') {
          colorClass = 'bg-red-500/20 border-red-500 text-red-400';
          Icon = <X className="h-5 w-5" />;
        }

        return (
          <React.Fragment key={step.step}>
            <div className="flex flex-col items-center gap-2 min-w-[120px]">
              <div className={`flex h-12 w-12 items-center justify-center rounded-full border-2 ${colorClass} transition-colors duration-300`}>
                {Icon ? Icon : <span className="text-lg font-bold">{step.step}</span>}
              </div>
              <div className="text-center">
                <div className="text-sm font-medium text-slate-200">{step.name}</div>
                <div className="text-xs text-slate-500 line-clamp-2 max-w-[150px]" title={step.description}>
                  {step.description}
                </div>
              </div>
            </div>
            
            {!isLast && (
              <div className="flex-1 h-0.5 min-w-[40px] mx-2 bg-slate-700 relative">
                <div className="absolute right-0 -top-1 w-2 h-2 border-t-2 border-r-2 border-slate-700 transform rotate-45" />
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

export default DagVisualizer;
