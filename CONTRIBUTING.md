# Contributing to Project Relay

We hold this codebase to rigorous production-grade standards. Because Project Relay executes consequential actions inside customer ERPs and CRM systems, every change must be verified against our security boundaries and audit invariants.

---

## 1. Development Environment Setup

1. **Install uv:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. **Install Python Dependencies:**
   ```bash
   uv sync --all-extras
   ```
3. **Start Local Services:**
   ```bash
   docker compose up -d postgres redis temporal
   ```
4. **Run Database Migrations:**
   ```bash
   uv run alembic upgrade head
   ```

---

## 2. Mandatory PR Checks (CI Pipeline)

Before submitting a Pull Request, verify that all local checks pass:

```bash
# 1. Lint and format checks
uv run ruff check .
uv run ruff format --check .

# 2. Strict type checking
uv run mypy --strict src/relay

# 3. Architectural import boundary enforcement
uv run lint-imports --config .importlinter

# 4. Unit and security tests
uv run pytest tests/unit -v
uv run pytest evals/probes/test_rls_coverage.py
uv run pytest evals/probes/test_cross_tenant.py

# 5. Core golden set acceptance scenarios (S01-S20)
uv run pytest evals/test_acceptance_scenarios.py
```

---

## 3. The Tool Authoring Checklist

When contributing a new tool or connector capability:
- [ ] Pydantic v2 `BaseModel` for both inputs and outputs.
- [ ] Side effect classification assigned (`read`, `write`, `external`, `destructive`, `financial`).
- [ ] Declarative policy rule defined in the policy module.
- [ ] Database-enforced idempotency key support.
- [ ] Cryptographic audit event emission verified.
- [ ] Compensation (undo) tool specified if side effect is financial or destructive.
- [ ] Regression test added to the golden evaluation set.

---

## 4. Architecture Decision Records (ADRs)

Any change affecting:
- Module layering
- Persistence or datastores
- Authorization semantics
- External protocols or SDK dependencies

MUST be accompanied by a new ADR under `docs/adr/`.
