import React from 'react';
import { CheckCircle2, AlertCircle } from 'lucide-react';

interface ComplianceBadgeProps {
  label: string;
  compliant: boolean;
}

const ComplianceBadge: React.FC<ComplianceBadgeProps> = ({ label, compliant }) => {
  return (
    <div className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border
      ${compliant ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}
    >
      {compliant ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
      {label}
    </div>
  );
};

export default ComplianceBadge;
