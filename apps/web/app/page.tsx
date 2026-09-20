import React from "react";
import { ActionCenterCard } from "../components/ActionCenterCard";

export default function OperatorConsolePage() {
  return (
    <main className="min-h-screen bg-slate-950 p-8 text-slate-100">
      <div className="max-w-5xl mx-auto space-y-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100">Project Relay — Operator Console</h1>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Governed AI execution layer · Active tenant: tnt_01J8XQPKZ7M4
          </p>
        </div>

        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-300 font-mono uppercase tracking-wider">
            Live Action Center Feed
          </h2>
          <ActionCenterCard
            runId="RUN 01J8XQPKZ7M4"
            channel="WhatsApp"
            sender="+971 5X XXX XXXX"
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
      </div>
    </main>
  );
}
