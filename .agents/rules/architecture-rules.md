# Architecture & Module Boundary Rules

These rules are enforced continuously during development and in CI via `import-linter`.

## 1. Module Layering Constraints
1. Modules in `src/relay/` may only import from lower layers in the following hierarchy:
   - `platform` (Layer 0 - Root)
   - `events` (Layer 1)
   - `audit` (Layer 2)
   - `identity` (Layer 3)
   - `conversations` (Layer 4)
   - `tickets` (Layer 5)
   - `knowledge` (Layer 6)
   - `decisions` (Layer 7)
   - `policy` (Layer 8)
   - `tools` (Layer 9)
   - `connectors`, `channels` (Layer 10)
   - `agent` (Layer 11)
   - `analytics` (Layer 12)
   - `api` (Layer 13 - Top)

2. Modules must NEVER import modules above them in this hierarchy.
3. No business logic in `src/relay/api/`. API endpoints are thin adapters that validate inputs and delegate to domain services.
4. Connectors and Channels must be accessed strictly through protocols defined in `tools/` and `channels/contracts.py`.

## 2. Cross-Module Mutations
- Direct cross-module database writes are strictly forbidden.
- To create a ticket from conversations, call `tickets.service.create_ticket()`, do not execute `session.add(Ticket(...))`.
