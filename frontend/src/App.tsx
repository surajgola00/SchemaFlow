import { useState } from 'react';
import Layout, { TabType } from './components/Layout';
import Studio from './components/Studio';
import ExecutionView from './components/ExecutionView';
import DataGrid from './components/DataGrid';
import InsightsPanel from './components/InsightsPanel';
import SchedulesPanel from './components/SchedulesPanel';
import History from './components/History';
import { Workflow } from './types';
import { Toaster } from 'sonner';

function App() {
  const [engineMode, setEngineMode] = useState<'mock' | 'live'>('mock');
  const [activeTab, setActiveTab] = useState<TabType>('studio');
  const [compiledWorkflow, setCompiledWorkflow] = useState<Workflow | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const handleCompileSuccess = (workflow: Workflow) => {
    setCompiledWorkflow(workflow);
    setActiveTab('studio');
  };

  const handleStartRun = (runId: string) => {
    setActiveRunId(runId);
    setActiveTab('execution');
  };

  const handleRunComplete = () => {
    setActiveTab('data');
  };

  return (
    <>
      <Toaster position="top-right" theme="dark" richColors closeButton />
      <Layout
        engineMode={engineMode}
        onEngineModeChange={setEngineMode}
        activeTab={activeTab}
        onTabSwitch={setActiveTab}
      >
        <div className="h-full flex-1 overflow-auto bg-[#0f1117]">
          {activeTab === 'studio' && (
            <Studio
              engineMode={engineMode}
              onCompile={handleCompileSuccess}
              compiledWorkflow={compiledWorkflow}
              onStartRun={handleStartRun}
              onTabSwitch={setActiveTab}
            />
          )}

          {activeTab === 'execution' && activeRunId && (
            <ExecutionView runId={activeRunId} onComplete={handleRunComplete} />
          )}

          {activeTab === 'execution' && !activeRunId && (
            <div className="flex h-full items-center justify-center text-slate-500 text-sm">
              No active run. Go to the Studio tab to compile and launch a workflow.
            </div>
          )}

          {activeTab === 'data' && activeRunId && (
            <DataGrid runId={activeRunId} />
          )}

          {activeTab === 'data' && !activeRunId && (
            <div className="flex h-full items-center justify-center text-slate-500 text-sm">
              No dataset loaded. Run a workflow or select one from History.
            </div>
          )}

          {activeTab === 'insights' && (
            <InsightsPanel runId={activeRunId} />
          )}

          {activeTab === 'schedules' && (
            <SchedulesPanel />
          )}

          {activeTab === 'history' && (
            <History
              onRerun={(runId) => {
                setActiveRunId(runId);
                setActiveTab('data');
              }}
            />
          )}
        </div>
      </Layout>
    </>
  );
}

export default App;
