# ADR 012: Append-Only Cryptographically Hash-Chained Audit Store

## Status
Accepted

## Context
Enterprise security audits and compliance standards (SOC 2, ISO 27001, HIPAA) require verifiable proof that operational logs have not been manipulated or truncated after the fact. Standard application logs stored in text files or search engines can be altered by privileged operators or compromised credentials.

## Decision
We enforce a **tamper-evident, cryptographically chained audit store**:
1. **Engine Enforcement:** The `audit_events` table is protected by a PostgreSQL `BEFORE UPDATE OR DELETE` trigger that raises an unrecoverable exception. The application role possesses `INSERT` and `SELECT` privileges only.
2. **Cryptographic Chaining:** Each audit event for a given tenant computes a SHA-256 digest linked to the preceding event:
   $$\text{hash}_n = \text{SHA256}(\text{hash}_{n-1} \parallel \text{canonical\_json}(\text{event}_n))$$
3. **Daily Proof Anchoring:** A scheduled verification worker validates chain integrity and exports the latest head hash to an Azure Blob Storage container protected by an immutable legal-hold policy.
4. **GDPR Right-to-Erasure:** Payload bodies are stored in offloaded blobs (`data_ref`). Fulfilling an erasure request deletes the referenced blob while leaving the audit record and its mathematical hash chain intact.

## Consequences
- **Positive:** Transforms standard logging into verifiable cryptographic proof of system behavior.
- **Negative:** Requires strict JSON canonicalization (deterministic key sorting) and transaction-level sequence serialization per tenant.
