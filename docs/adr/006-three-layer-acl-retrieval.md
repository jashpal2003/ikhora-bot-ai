# ADR 006: Three-Layer ACL-Aware Retrieval with On-Behalf-Of (OBO) Enforcement

## Status
Accepted

## Context
Retrieving enterprise documents (SharePoint, OneDrive) that the requesting user is unauthorized to view represents a critical security violation. Using application-wide permissions (`Sites.Read.All`) creates an accidental permission-bypass vulnerability if application-layer filtering fails.

## Decision
We enforce a **Three-Layer Access Control Model** backed by Microsoft Graph On-Behalf-Of (OBO) user token exchange:
1. **OBO First:** Queries originating from enterprise users (e.g., Teams) always use the user's delegated identity. Customer-facing channels are strictly restricted to public corpora.
2. **Layer 1 (Index-Time):** Ingest and store document ACLs in `acl_grants` along with an `acl_hash` for change detection. Delta queries track ACL modifications separately from content bodies.
3. **Layer 2 (Query-Time SQL Filtering):** Expand user Entra group memberships (`transitiveMemberOf`) and evaluate permissions directly inside the SQL `WHERE` clause before vector or BM25 ranking.
4. **Layer 3 (Pre-Release OBO Verification):** The top surviving candidates ($K \approx 8$) undergo real-time batched permission verification via Microsoft Graph before any content is injected into LLM context.

## Consequences
- **Positive:** Eliminates permission staleness and data leakage risks with defense-in-depth verification.
- **Negative:** Adds a batched Graph API call latency penalty to final retrieval generation (mitigated by a 5-minute cache per `[user, doc, acl_hash]`).
