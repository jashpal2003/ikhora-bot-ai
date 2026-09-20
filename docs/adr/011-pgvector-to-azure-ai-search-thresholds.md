# ADR 011: pgvector as Initial Vector Engine with Defined Azure AI Search Migration Thresholds

## Status
Accepted

## Context
Deploying an external dedicated search cluster (e.g., Azure AI Search, Pinecone, Qdrant) at project inception introduces significant operational cost and splits transactional document metadata across network boundaries. PostgreSQL Flexible Server natively supports `pgvector` alongside standard relational queries and GIN full-text indexes (`tsvector`).

## Decision
We adopt **`pgvector` (0.8+ with HNSW indexing)** co-located within the primary PostgreSQL database for Phase 1 and define explicit migration triggers:
1. Reciprocal Rank Fusion (RRF) combines `pgvector` HNSW cosine similarity scores with `tsvector` BM25 keyword rankings.
2. The search interface is abstracted behind a clean `Retriever` protocol to facilitate painless migration.

### Migration Triggers to Azure AI Search:
- Vector corpus exceeds **5–10 million chunks** per database instance.
- Retrieval p95 latency exceeds **400ms** after query and index tuning.
- HNSW index build and maintenance begins degrading primary OLTP transactional throughput.
- An enterprise customer contract mandates hardware-isolated security trimming at the vector engine tier.

## Consequences
- **Positive:** Zero auxiliary search infrastructure, transactional ACL updates, and simplified local development.
- **Negative:** Dedicated vector search features (e.g., custom language analyzers, semantic reranking) must be handled at the application layer.
