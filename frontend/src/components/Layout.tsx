import React, { useEffect, useState } from 'react';
import { Zap, Cpu, ShieldCheck } from 'lucide-react';
import { api } from '../api/client';
import { SystemStatus } from '../types';

export type TabType = 'studio' | 'execution' | 'data' | 'insights' | 'schedules' | 'history';

interface LayoutProps {
  children: React.ReactNode;
  engineMode: 'mock' | 'live';
  onEngineModeChange: (mode: 'mock' | 'live') => void;
  activeTab: TabType;
  onTabSwitch: (tab: TabType) => void;
}

const Layout: React.FC<LayoutProps> = ({
  children,
  engineMode,
  onEngineModeChange,
  activeTab,
  onTabSwitch,
}) => {
  const [sysStatus, setSysStatus] = useState<SystemStatus | null>(null);
  const [isOffline, setIsOffline] = useState(false);

  const checkStatus = () => {
    api.systemStatus()
      .then((status) => {
        setSysStatus(status);
        setIsOffline(false);
      })
      .catch(() => {
        setIsOffline(true);
        setSysStatus({ llm_mode: 'mock', model: 'mock', search_provider: 'duckduckgo_html', version: '2.0' });
      });
  };

  useEffect(() => {
    checkStatus();
  }, []);

  const tabs: Array<{ id: TabType; label: string }> = [
    { id: 'studio', label: 'Studio' },
    { id: 'execution', label: 'Execution' },
    { id: 'data', label: 'Data Explorer' },
    { id: 'insights', label: 'Insights & Quality' },
    { id: 'schedules', label: 'Schedules' },
    { id: 'history', label: 'History & Diff' },
  ];

  return (
    <div className="flex h-screen w-screen flex-col bg-[#0f1117] text-slate-100">
      {isOffline && (
        <div className="bg-red-950/80 border-b border-red-700/60 px-4 py-2 text-xs text-red-200 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-red-400 animate-pulse" />
            <span>
              <strong>Backend Offline:</strong> Unable to connect to backend server at {(import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000'}. Ensure the FastAPI server is running.
            </span>
          </div>
          <button
            onClick={checkStatus}
            className="px-2.5 py-1 bg-red-800 hover:bg-red-700 rounded text-white font-medium text-[11px] transition-colors"
          >
            Retry Connection
          </button>
        </div>
      )}
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-surface px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10 border border-indigo-500/30">
            <Zap className="h-5 w-5 text-indigo-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-lg font-bold text-transparent">
                SchemaFlow
              </h1>
            </div>
            <p className="text-[11px] text-slate-400 flex items-center gap-1">
              <ShieldCheck className="h-3 w-3 text-emerald-400" /> Evidence-Verified Data Intelligence
            </p>
          </div>
        </div>

        <nav className="flex items-center space-x-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabSwitch(tab.id)}
              className={`rounded-lg px-3.5 py-1.5 text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-slate-800 text-white font-semibold shadow-sm border border-slate-700'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          {sysStatus && (
            <div className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${
              sysStatus.llm_mode === 'live'
                ? 'border-emerald-500/40 bg-emerald-950/40 text-emerald-300'
                : 'border-amber-500/40 bg-amber-950/40 text-amber-300'
            }`}>
              <span className={`h-2 w-2 rounded-full ${
                sysStatus.llm_mode === 'live' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
              }`} />
              <Cpu className="h-3.5 w-3.5" />
              <span>{sysStatus.llm_mode === 'live' ? 'LIVE LLM:' : 'MOCK LLM:'}</span>
              <span className="font-semibold">
                {sysStatus.llm_mode === 'live' ? sysStatus.model : 'Deterministic Mock'}
              </span>
            </div>
          )}

          <div className="flex items-center rounded-full border border-border bg-[#0f1117] p-1">
            <button
              onClick={() => onEngineModeChange('mock')}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                engineMode === 'mock'
                  ? 'bg-amber-500 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Runs deterministically offline with fixture datasets"
            >
              Demo Replay
            </button>
            <button
              onClick={() => onEngineModeChange('live')}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                engineMode === 'live'
                  ? 'bg-emerald-600 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Crawls live web sources with SSRF and robots.txt enforcement"
            >
              Live Pipeline
            </button>
          </div>
        </div>
      </header>

      <main className="flex min-h-0 flex-1 flex-col">{children}</main>
    </div>
  );
};

export default Layout;
