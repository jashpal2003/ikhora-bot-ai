---
name: relay-workflow
description: >-
  Workflows, testing patterns, and durable execution best practices for Project Relay.
  Use when creating tools, defining policy rules, writing Temporal agent workflows,
  or testing acceptance scenarios S01-S20.
---

# Project Relay Development & Workflow Skill

This skill provides operational patterns for extending Project Relay's agent workflows, connectors, policy engines, and audit verifications.

---

## 1. Adding a New Tool

When creating a new tool under `src/relay/tools/`:

1. Define the Pydantic v2 input and output schemas:
   ```python
   class CreateCaseInput(BaseModel):
       customer_id: str
       title: str
       severity: Literal["low", "medium", "high"]

   class CreateCaseOutput(BaseModel):
       case_id: str
       tracking_url: str
   ```

2. Declare the `ToolSpec` with side effect classification:
   ```python
   case_tool = ToolSpec(
       name="dataverse.create_case",
       version="1.0.0",
       description="Create a support case in Microsoft Dataverse.",
       input_schema=CreateCaseInput,
       output_schema=CreateCaseOutput,
       side_effect="write",
       required_scopes=["Cases.Write"],
       identity_mode="obo",
       idempotent=True,
       timeout_ms=10000,
       retry=RetryPolicy(maximum_attempts=3),
       compensation="dataverse.cancel_case",
       audit="full"
   )
   ```

3. Add matching declarative policy rules in `src/relay/policy/rules.yaml`.
4. Implement the compensation method if the tool has `write`, `destructive`, or `financial` side effects.

---

## 2. Temporal Workflow Determinism Rules

Inside `src/relay/agent/workflow.py`:
- **NEVER** use `datetime.now()` or `time.time()` (use `workflow.now()`).
- **NEVER** use `random.choice()` or `uuid.uuid4()` (use deterministic workflow seeds).
- **NEVER** perform direct I/O, database calls, or HTTP requests inside workflow code. All I/O must run inside `workflow.execute_activity(...)`.
- Use `workflow.wait_condition(...)` or `workflow.wait_for_signal(...)` when waiting for human approvals.

---

## 3. Testing Acceptance Scenarios

Test suites for scenarios S01–S20 are located in `evals/`:
```bash
# Run all golden set evaluations
uv run pytest evals/test_acceptance_scenarios.py -v

# Run ACL-specific negative tests (S07, S08)
uv run pytest evals/test_acceptance_scenarios.py -k "test_acl"

# Run prompt injection red-team regression (S18)
uv run pytest evals/test_acceptance_scenarios.py -k "test_injection"
```
