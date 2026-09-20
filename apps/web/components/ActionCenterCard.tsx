"use client";

import React from "react";
import { CheckCircle, Shield, AlertTriangle, RotateCcw, Download, ExternalLink } from "lucide-react";

export interface ActionCenterCardProps {
  runId: string;
  channel: string;
  sender: string;
  timeRange: string;
  costUsd: number;
  what: string;
  why: string;
  who: string;
  data: string;
  evidence: string;
  policy: string;
  decision: string;
  result: string;
  budget: string;
}

export const ActionCenterCard: React.FC<ActionCenterCardProps> = ({
  runId,
  channel,
  sender,
  timeRange,
  costUsd,
  what,
  why,
  who,
  data,
  evidence,
  policy,
  decision,
  result,
  budget,
}) => {
  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/95 p-6 shadow-2xl backdrop-blur font-mono text-xs text-slate-300">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between border-b border-slate-800 pb-4 mb-4 gap-2">
        <div className="flex items-center gap-3">
          <span className="rounded bg-indigo-500/20 px-2 py-1 font-semibold text-indigo-400">
            {runId}
          </span>
          <span className="text-slate-400">·</span>
          <span className="text-slate-200">{channel}</span>
          <span className="text-slate-400">·</span>
          <span className="text-slate-400">{sender}</span>
          <span className="text-slate-400">·</span>
          <span className="text-slate-400">{timeRange}</span>
        </div>
        <div className="rounded bg-emerald-500/10 px-2.5 py-1 text-emerald-400 font-medium">
          ${costUsd.toFixed(4)}
        </div>
      </div>

      {/* Structured Fields Grid */}
      <div className="grid grid-cols-1 md:grid-cols-[100px_1fr] gap-y-3.5 gap-x-4 items-baseline">
        <div className="text-slate-500 uppercase tracking-wider font-semibold">WHAT</div>
        <div className="text-slate-100 font-medium flex items-center gap-2">
          <span className="text-emerald-400">✓</span> {what}
        </div>

        <div className="text-slate-500 uppercase tracking-wider font-semibold">WHY</div>
        <div className="text-slate-300">{why}</div>

        <div className="text-slate-500 uppercase tracking-wider font-semibold">WHO</div>
        <div className="text-slate-300 text-indigo-300">{who}</div>

        <div className="text-slate-500 uppercase tracking-wider font-semibold">DATA</div>
        <div className="text-slate-300">{data}</div>

        <div className="text-slate-500 uppercase tracking-wider font-semibold">EVIDENCE</div>
        <div className="text-slate-300 flex items-center gap-2">
          <Shield className="w-3.5 h-3.5 text-blue-400" />
          <span>{evidence}</span>
        </div>

        <div className="text-slate-500 uppercase tracking-wider font-semibold">POLICY</div>
        <div className="text-emerald-300 bg-emerald-950/30 px-2 py-0.5 rounded border border-emerald-800/40 inline-block">
          {policy}
        </div>

        <div className="text-slate-500 uppercase tracking-wider font-semibold">DECISION</div>
        <div className="text-slate-300">{decision}</div>

        <div className="text-slate-500 uppercase tracking-wider font-semibold">RESULT</div>
        <div className="text-emerald-400 flex items-center gap-1.5">
          <CheckCircle className="w-3.5 h-3.5" />
          {result}
        </div>

        <div className="text-slate-500 uppercase tracking-wider font-semibold">BUDGET</div>
        <div className="text-slate-400">{budget}</div>
      </div>

      {/* Action Bar */}
      <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-slate-800 pt-4">
        <button className="flex items-center gap-1.5 rounded bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700 transition">
          <RotateCcw className="w-3.5 h-3.5" /> Replay
        </button>
        <button className="flex items-center gap-1.5 rounded bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700 transition">
          <Download className="w-3.5 h-3.5" /> Export Audit JSON
        </button>
        <button className="flex items-center gap-1.5 rounded bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700 transition">
          <ExternalLink className="w-3.5 h-3.5" /> Open Trace
        </button>
        <button className="flex items-center gap-1.5 rounded bg-rose-950/40 border border-rose-800/30 px-3 py-1.5 text-xs text-rose-400 hover:bg-rose-900/50 transition ml-auto">
          <AlertTriangle className="w-3.5 h-3.5" /> Report Incorrect
        </button>
      </div>
    </div>
  );
};
