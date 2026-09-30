import { useState } from 'react';
import Layout from './components/Layout';
import Studio from './components/Studio';
import ExecutionView from './components/ExecutionView';
import DataGrid from './components/DataGrid';
import History from './components/History';
import { Workflow } from './types';

function App() {
  const [engineMode, setEngineMode] = useState<'mock' | 'live'>('mock');
  const [activeTab, setActiveTab] = useState<'studio' | 'execution' | 'data' | 'history'>('studio');
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
    <Layout
      engineMode={engineMode}
      onEngineModeChange={setEngineMode}
      activeTab={activeTab}
      onTabSwitch={setActiveTab}
    >
      <div className="h-full flex-1 overflow-auto bg-[#0f1117] p-6">
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
          <ExecutionView
            runId={activeRunId}
            onComplete={handleRunComplete}
          />
        )}
        {activeTab === 'execution' && !activeRunId && (
          <div className="flex h-full items-center justify-center text-slate-500">
            No active run. Go to Studio to start a run.
          </div>
        )}
        {activeTab === 'data' && activeRunId && (
          <DataGrid runId={activeRunId} />
        )}
        {activeTab === 'data' && !activeRunId && (
          <div className="flex h-full items-center justify-center text-slate-500">
            No data available. Start a run first.
          </div>
        )}
        {activeTab === 'history' && (
          <History onRerun={(runId) => {
            setActiveRunId(runId);
            setActiveTab('execution');
          }} />
        )}
      </div>
    </Layout>
  );
}

export default App;
