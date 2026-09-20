"use client";

import React, { useState } from "react";
import { ActionCenterCard } from "../components/ActionCenterCard";
import { MessageSquare, ShieldAlert, CheckCircle2, Search, UserCheck, Clock, Send } from "lucide-react";

interface ConversationItem {
  id: string;
  sender: string;
  channel: string;
  snippet: string;
  time: string;
  status: "open" | "escalated" | "resolved";
  priority: "normal" | "high" | "urgent";
}

const SAMPLE_CONVERSATIONS: ConversationItem[] = [
  {
    id: "cnv_01J8X01",
    sender: "+971 50 123 4567",
    channel: "WhatsApp",
    snippet: "Package arrived with damaged glass on widget 8281.",
    time: "14:03",
    status: "open",
    priority: "high",
  },
  {
    id: "cnv_01J8X02",
    sender: "sarah.ops@contoso.com",
    channel: "Teams",
    snippet: "Can you pull the Q3 customer delivery report?",
    time: "13:45",
    status: "open",
    priority: "normal",
  },
  {
    id: "cnv_01J8X03",
    sender: "Visitor #4412",
    channel: "Web",
    snippet: "What are your EU return guidelines?",
    time: "12:30",
    status: "resolved",
    priority: "normal",
  },
];

export default function OperatorConsolePage() {
  const [selectedConvId, setSelectedConvId] = useState("cnv_01J8X01");
  const [activeTab, setActiveTab] = useState<"action_center" | "conversation">("action_center");
  const [replyInput, setReplyInput] = useState("");

  const activeConv = SAMPLE_CONVERSATIONS.find((c) => c.id === selectedConvId) || SAMPLE_CONVERSATIONS[0];

  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-100 font-sans overflow-hidden">
      {/* Sidebar: Navigation & Brand */}
      <aside className="w-64 border-r border-slate-800/80 bg-slate-900/60 p-4 flex flex-col justify-between">
        <div className="space-y-6">
          <div className="flex items-center gap-2.5 px-2">
            <div className="h-7 w-7 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white text-sm shadow-md shadow-indigo-500/30">
              R
            </div>
            <div>
              <h1 className="font-bold text-sm tracking-tight text-slate-100">Project Relay</h1>
              <p className="text-[10px] text-slate-400 font-mono">Workforce Console</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1 text-xs">
            <button
              onClick={() => setActiveTab("action_center")}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg font-medium transition ${
                activeTab === "action_center"
                  ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                  : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
              }`}
            >
              <ShieldAlert className="w-4 h-4 text-indigo-400" />
              <span>Action Center & Audit</span>
            </button>
            <button
              onClick={() => setActiveTab("conversation")}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg font-medium transition ${
                activeTab === "conversation"
                  ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                  : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
              }`}
            >
              <MessageSquare className="w-4 h-4 text-emerald-400" />
              <span>Unified Inbox</span>
            </button>
          </nav>
        </div>

        {/* Tenant Footer */}
        <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800 text-[11px] font-mono text-slate-400">
          <div className="flex items-center gap-2 text-slate-300 font-medium">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            tnt_01J8XQPKZ7M4
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Tenant Scope Active (RLS)</div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Inbox Panel */}
        <section className="w-80 border-r border-slate-800/80 bg-slate-900/30 flex flex-col">
          <div className="p-4 border-b border-slate-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono">Live Ingress</h2>
              <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full">
                3 active
              </span>
            </div>
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search conversations..."
                className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Conversation List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/40">
            {SAMPLE_CONVERSATIONS.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedConvId(c.id)}
                className={`w-full text-left p-3.5 transition flex flex-col gap-1.5 ${
                  selectedConvId === c.id ? "bg-indigo-600/10 border-l-2 border-indigo-500" : "hover:bg-slate-800/30"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-200 flex items-center gap-1.5">
                    <span className="text-[10px] font-mono text-indigo-400">{c.channel}</span>
                    <span className="text-slate-400">·</span>
                    {c.sender}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">{c.time}</span>
                </div>
                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{c.snippet}</p>
              </button>
            ))}
          </div>
        </section>

        {/* Detail Panel */}
        <section className="flex-1 flex flex-col bg-slate-950 overflow-y-auto p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
            <div>
              <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <span>{activeConv.sender}</span>
                <span className="text-xs font-mono text-slate-400">({activeConv.id})</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5 font-mono">
                Channel: {activeConv.channel} · Identity Tier: Verified (OTP) · Autonomy: Assist
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 font-medium border border-emerald-500/20">
                Policy Active
              </span>
            </div>
          </div>

          {/* Action Center Live Card */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-indigo-400" />
              Governed Execution & Compliance Verification
            </h3>
            <ActionCenterCard
              runId="RUN 01J8XQPKZ7M4"
              channel="WhatsApp"
              sender={activeConv.sender}
              timeRange="14:03:11 → 14:03:19"
              costUsd={0.0041}
              what="Created case CAS-4471 in Dataverse"
              why="Customer reported damaged order; policy requires case for claims"
              who='Agent "Support Employee v7" on behalf of priya@customer.com'
              data="Order 8281 (Shopify, read 14:03:14) · Contact verified via OTP"
              evidence="Damaged Goods Policy §4.2 (SharePoint, v12, 4 days old) ✓ validated"
              policy="refund_threshold — amount $42 below $50 → auto-approved"
              decision="intent=damage_claim (0.94) · priority=high (0.88) · human=no (0.21)"
              result="CAS-4471 created · Teams notified #support · reply sent 14:03:19"
              budget="4 / 12 steps · 8.2s / 90s · $0.0041 / $0.50"
            />
          </div>

          {/* Chat / Operator Reply Box */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
            <h4 className="text-xs font-semibold text-slate-300 font-mono">Operator Reply / Override</h4>
            <div className="flex gap-2">
              <input
                type="text"
                value={replyInput}
                onChange={(e) => setReplyInput(e.target.value)}
                placeholder="Type response or human instruction to customer..."
                className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={() => setReplyInput("")}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-4 py-2 rounded-lg font-medium flex items-center gap-1.5 transition"
              >
                <Send className="w-3.5 h-3.5" /> Send Reply
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
