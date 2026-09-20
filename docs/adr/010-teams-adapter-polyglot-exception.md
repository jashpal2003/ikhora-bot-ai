# ADR 010: Polyglot Exception for the Microsoft Teams Adapter

## Status
Accepted

## Context
Microsoft's official Python support for the new Microsoft 365 Agents SDK (`Microsoft.Agents.*`) lags significantly behind .NET (C#) and TypeScript. Legacy Bot Framework v4 is deprecated, and TeamsFx reaches end of community support in September 2026. Building a production-grade Teams enterprise integration in Python would require unsupported preview SDKs or manual protocol emulation.

## Decision
We grant an explicit **polyglot exception** for the Microsoft Teams channel adapter:
- Author the Teams adapter in TypeScript using `@microsoft/agents-hosting` and `@microsoft/agents-hosting-teams` (or C#).
- Deploy it as a dedicated sidecar or standalone micro-service under `apps/teams-adapter/`.
- The adapter translates native Teams activities into Project Relay's standardized `MessageEnvelope` protocol and forwards them over internal HTTP/gRPC to `relay-gateway`.
- All other core modulith services remain strictly in Python 3.12.

## Consequences
- **Positive:** Uses fully-supported, GA-grade enterprise Microsoft SDKs for Teams integration.
- **Negative:** Introduces a second runtime (Node.js/TypeScript or .NET) in CI/CD build pipelines.
