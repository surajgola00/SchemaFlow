import React from 'react';
import { SchemaField } from '../types';

const typeColors: Record<string, string> = {
  string: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
  url: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  number: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  integer: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  currency: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  boolean: 'bg-pink-500/10 text-pink-400 border-pink-500/20',
  email: 'bg-green-500/10 text-green-400 border-green-500/20',
  date: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  phone: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  enum: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  list: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
};

const SchemaTag: React.FC<{ field: SchemaField }> = ({ field }) => {
  const colorClass = typeColors[field.type] || typeColors.string;

  return (
    <div className={`flex items-center gap-2 rounded-full border px-3 py-1 text-sm ${colorClass}`} title={field.description}>
      <span className="font-semibold">{field.name}</span>
      <span className="text-xs opacity-75">({field.type})</span>
      {field.required && <span className="text-xs font-bold text-red-400">*</span>}
    </div>
  );
};

export default SchemaTag;
