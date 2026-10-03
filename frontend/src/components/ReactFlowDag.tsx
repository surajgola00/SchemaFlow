import React, { useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  Handle,
  Position,
  MarkerType,
} from 'reactflow';
import {
  Globe,
  Download,
  Sparkles,
  Wand2,
  ShieldCheck,
  Layers,
  Award,
  CheckCircle2,
  HelpCircle,
  Loader2,
  Check,
  X,
  MinusCircle,
} from 'lucide-react';
import { DagStep } from '../types';

export interface NodeStatusInfo {
  status: 'pending' | 'running' | 'succeeded' | 'completed' | 'failed' | 'skipped' | 'cancelled';
  items_in?: number;
  items_out?: number;
  error?: string | null;
}

interface ReactFlowDagProps {
  steps?: DagStep[];
  dagNodes?: Array<{
    id: string;
    type: string;
    label: string;
    depends_on?: string[];
  }>;
  nodeStatuses?: Record<string, NodeStatusInfo>;
  interactive?: boolean;
  height?: number | string;
}

const getNodeIcon = (type: string) => {
  switch (type) {
    case 'discover_sources':
      return <Globe className="h-4 w-4 text-sky-400" />;
    case 'fetch':
      return <Download className="h-4 w-4 text-blue-400" />;
    case 'extract':
      return <Sparkles className="h-4 w-4 text-purple-400" />;
    case 'normalize':
      return <Wand2 className="h-4 w-4 text-indigo-400" />;
    case 'validate':
      return <ShieldCheck className="h-4 w-4 text-emerald-400" />;
    case 'dedupe':
      return <Layers className="h-4 w-4 text-amber-400" />;
    case 'score':
      return <Award className="h-4 w-4 text-orange-400" />;
    case 'finalize':
      return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
    default:
      return <HelpCircle className="h-4 w-4 text-slate-400" />;
  }
};

const CustomDagNode: React.FC<{ data: any }> = ({ data }) => {
  const { label, type, status = 'pending', items_in, items_out, error } = data;

  let borderClass = 'border-slate-700 bg-surface/90 text-slate-300';
  let badgeClass = 'bg-slate-800 text-slate-400';
  let StatusIcon = null;

  if (status === 'completed' || status === 'succeeded') {
    borderClass = 'border-emerald-500/80 bg-emerald-950/40 text-emerald-200 shadow-emerald-950/50 shadow-md';
    badgeClass = 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
    StatusIcon = <Check className="h-3 w-3 text-emerald-400" />;
  } else if (status === 'running') {
    borderClass = 'border-indigo-500 bg-indigo-950/50 text-indigo-200 ring-2 ring-indigo-500/40 ring-offset-1 ring-offset-[#0f1117] animate-pulse';
    badgeClass = 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30';
    StatusIcon = <Loader2 className="h-3 w-3 animate-spin text-indigo-400" />;
  } else if (status === 'failed') {
    borderClass = 'border-red-500/80 bg-red-950/40 text-red-200';
    badgeClass = 'bg-red-500/20 text-red-300 border border-red-500/30';
    StatusIcon = <X className="h-3 w-3 text-red-400" />;
  } else if (status === 'skipped') {
    borderClass = 'border-slate-700 bg-slate-900/60 text-slate-500 opacity-60';
    badgeClass = 'bg-slate-800 text-slate-500';
    StatusIcon = <MinusCircle className="h-3 w-3 text-slate-500" />;
  }

  return (
    <div className={`min-w-[170px] max-w-[210px] rounded-xl border-2 px-3 py-2.5 shadow-lg backdrop-blur transition-all ${borderClass}`}>
      <Handle type="target" position={Position.Left} className="!w-2 !h-2 !bg-slate-500 !border-none" />
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5 min-w-0">
          {getNodeIcon(type)}
          <span className="text-xs font-bold text-white truncate" title={label}>
            {label}
          </span>
        </div>
        {StatusIcon}
      </div>

      <div className="flex items-center justify-between text-[10px] gap-1">
        <span className="font-mono text-slate-400 capitalize truncate">{type.replace('_', ' ')}</span>
        <span className={`rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider ${badgeClass}`}>
          {status}
        </span>
      </div>

      {(items_in !== undefined || items_out !== undefined) && (
        <div className="mt-1.5 pt-1 border-t border-slate-700/50 flex justify-between text-[10px] font-mono text-slate-300">
          <span>in: <strong className="text-white">{items_in ?? 0}</strong></span>
          <span>out: <strong className="text-emerald-400">{items_out ?? 0}</strong></span>
        </div>
      )}

      {error && (
        <div className="mt-1 text-[9px] text-red-400 truncate" title={error}>
          {error}
        </div>
      )}
      <Handle type="source" position={Position.Right} className="!w-2 !h-2 !bg-indigo-500 !border-none" />
    </div>
  );
};

const nodeTypes = {
  customDagNode: CustomDagNode,
};

export const ReactFlowDag: React.FC<ReactFlowDagProps> = ({
  steps,
  dagNodes,
  nodeStatuses = {},
  interactive = true,
  height = 240,
}) => {
  // Normalize input nodes
  const rawNodes = useMemo(() => {
    if (dagNodes && dagNodes.length > 0) {
      return dagNodes;
    }
    if (steps && steps.length > 0) {
      return steps.map((s, idx) => ({
        id: s.id || `n${s.step}`,
        type: s.type || 'fetch',
        label: s.name,
        depends_on: idx > 0 ? [steps[idx - 1].id || `n${steps[idx - 1].step}`] : [],
      }));
    }
    return [];
  }, [dagNodes, steps]);

  // Build nodes & edges layout (horizontal flow)
  const { nodes, edges } = useMemo(() => {
    if (!rawNodes || rawNodes.length === 0) {
      return { nodes: [], edges: [] };
    }

    // Topological level calculation
    const inDegree: Record<string, number> = {};
    const adj: Record<string, string[]> = {};
    rawNodes.forEach((n) => {
      inDegree[n.id] = 0;
      adj[n.id] = [];
    });
    rawNodes.forEach((n) => {
      (n.depends_on || []).forEach((dep) => {
        if (adj[dep]) adj[dep].push(n.id);
        inDegree[n.id] = (inDegree[n.id] || 0) + 1;
      });
    });

    const level: Record<string, number> = {};
    const queue = rawNodes.filter((n) => (inDegree[n.id] || 0) === 0).map((n) => n.id);
    queue.forEach((id) => (level[id] = 0));

    while (queue.length > 0) {
      const u = queue.shift()!;
      (adj[u] || []).forEach((v) => {
        level[v] = Math.max(level[v] || 0, (level[u] || 0) + 1);
        inDegree[v] -= 1;
        if (inDegree[v] === 0) queue.push(v);
      });
    }

    // Assign positions based on level
    const levelCounts: Record<number, number> = {};
    const flowNodes: Node[] = rawNodes.map((n) => {
      const lvl = level[n.id] ?? 0;
      const countInLevel = levelCounts[lvl] ?? 0;
      levelCounts[lvl] = countInLevel + 1;

      const x = 30 + lvl * 230;
      const y = 30 + countInLevel * 105;

      const st = nodeStatuses[n.id] || { status: 'pending' };

      return {
        id: n.id,
        type: 'customDagNode',
        position: { x, y },
        data: {
          label: n.label,
          type: n.type,
          status: st.status,
          items_in: st.items_in,
          items_out: st.items_out,
          error: st.error,
        },
      };
    });

    // Build edges
    const flowEdges: Edge[] = [];
    rawNodes.forEach((n) => {
      (n.depends_on || []).forEach((dep) => {
        const sourceStatus = nodeStatuses[dep]?.status;
        const isAnimated = sourceStatus === 'running';
        const strokeColor =
          sourceStatus === 'completed' || sourceStatus === 'succeeded'
            ? '#10b981'
            : sourceStatus === 'running'
            ? '#6366f1'
            : '#475569';

        flowEdges.push({
          id: `e-${dep}-${n.id}`,
          source: dep,
          target: n.id,
          animated: isAnimated,
          style: { stroke: strokeColor, strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: strokeColor,
            width: 14,
            height: 14,
          },
        });
      });
    });

    return { nodes: flowNodes, edges: flowEdges };
  }, [rawNodes, nodeStatuses]);

  if (nodes.length === 0) {
    return (
      <div className="flex h-36 w-full items-center justify-center rounded-xl border border-dashed border-slate-800 text-xs text-slate-500">
        No DAG pipeline generated yet. Compile a prompt to view the execution graph.
      </div>
    );
  }

  return (
    <div
      style={{ height }}
      className="w-full rounded-xl border border-border bg-[#0b0d13] overflow-hidden relative shadow-inner"
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={1.5}
        panOnDrag={interactive}
        zoomOnScroll={interactive}
        nodesDraggable={interactive}
        nodesConnectable={false}
        elementsSelectable={interactive}
      >
        <Background color="#1e293b" gap={16} size={1} />
        {interactive && <Controls className="!bg-surface !border-slate-700 !fill-slate-300" />}
      </ReactFlow>
    </div>
  );
};

export default ReactFlowDag;
