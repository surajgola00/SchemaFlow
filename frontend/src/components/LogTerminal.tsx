import React, { useEffect, useRef } from 'react';
import { LogEntry } from '../types';

const LogTerminal: React.FC<{ logs: LogEntry[] }> = ({ logs }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'INFO': return 'text-blue-400';
      case 'SUCCESS': return 'text-green-400';
      case 'WARNING': return 'text-yellow-400';
      case 'ERROR': return 'text-red-400';
      default: return 'text-slate-300';
    }
  };

  return (
    <div className="h-96 w-full overflow-y-auto rounded-lg bg-[#0d1117] p-4 font-mono text-sm shadow-inner border border-border">
      {logs.length === 0 ? (
        <div className="text-slate-500">Waiting for logs...</div>
      ) : (
        <div className="space-y-1">
          {logs.map((log, i) => (
            <div key={i} className="flex gap-3 hover:bg-white/5 px-2 py-0.5 rounded">
              <span className="text-slate-500 shrink-0">[{log.timestamp}]</span>
              <span className={`font-semibold shrink-0 w-20 ${getLevelColor(log.level)}`}>[{log.level}]</span>
              <span className="text-slate-300 break-words">{log.message}</span>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
};

export default LogTerminal;
