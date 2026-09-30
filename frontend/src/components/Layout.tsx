import React from 'react';
import { Zap } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  engineMode: 'mock' | 'live';
  onEngineModeChange: (mode: 'mock' | 'live') => void;
  activeTab: 'studio' | 'execution' | 'data' | 'history';
  onTabSwitch: (tab: 'studio' | 'execution' | 'data' | 'history') => void;
}

const Layout: React.FC<LayoutProps> = ({
  children,
  engineMode,
  onEngineModeChange,
  activeTab,
  onTabSwitch,
}) => {
  const tabs = [
    { id: 'studio', label: 'Studio' },
    { id: 'execution', label: 'Execution' },
    { id: 'data', label: 'Data Explorer' },
    { id: 'history', label: 'History' },
  ] as const;

  return (
    <div className="flex h-screen w-screen flex-col bg-[#0f1117] text-slate-100">
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-surface px-6">
        <div className="flex items-center gap-2">
          <Zap className="h-6 w-6 text-indigo-500" />
          <h1 className="bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-xl font-bold text-transparent">
            SchemaFlow
          </h1>
        </div>

        <nav className="flex items-center space-x-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabSwitch(tab.id)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-[#0f1117] text-white underline decoration-indigo-500 decoration-2 underline-offset-8'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <div className="flex items-center rounded-full border border-border bg-[#0f1117] p-1">
            <button
              onClick={() => onEngineModeChange('mock')}
              className={`rounded-full px-4 py-1.5 text-xs font-semibold transition-colors ${
                engineMode === 'mock'
                  ? 'bg-amber-500 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Demo Mock
            </button>
            <button
              onClick={() => onEngineModeChange('live')}
              className={`rounded-full px-4 py-1.5 text-xs font-semibold transition-colors ${
                engineMode === 'live'
                  ? 'bg-green-500 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Live Web
            </button>
          </div>
        </div>
      </header>

      <main className="flex min-h-0 flex-1 flex-col">{children}</main>
    </div>
  );
};

export default Layout;
