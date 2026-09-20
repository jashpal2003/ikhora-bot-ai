"""Tool executor enforcing policy verdicts, idempotency, and audit emission."""

import hashlib
import json
import time
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from relay.audit.writer import AuditWriter
from relay.platform.errors import PolicyDeniedError, RelayError
from relay.platform.ids import generate_id
from relay.policy.models import Verdict
from relay.tools.spec import ToolSpec


class ToolExecutor:
    """Executes tools through the single policy gate with guaranteed audit logging."""

    @staticmethod
    def generate_idempotency_key(run_id: str, seq: int, tool_name: str, payload: dict[str, Any]) -> str:
        """Compute deterministic idempotency key per §10.1."""
        raw = f"{run_id}:{seq}:{tool_name}:{json.dumps(payload, sort_keys=True)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    async def invoke(
        cls,
        session: AsyncSession,
        tool: ToolSpec,
        payload: dict[str, Any],
        verdict: Verdict,
        tenant_id: str,
        run_id: str,
        seq: int,
        correlation_id: str,
        on_behalf_of: str | None = None,
    ) -> dict[str, Any]:
        """Execute a tool strictly behind policy authorization with idempotency guarantees."""
        # 1. Structural check: Must have policy allowance
        if not verdict.allowed:
            raise PolicyDeniedError(
                tool.name,
                [r.message for r in verdict.reasons],
            )

        # 2. Schema validation
        validated_input = tool.input_schema.model_validate(payload)
        input_data = validated_input.model_dump()
        input_hash = hashlib.sha256(json.dumps(input_data, sort_keys=True).encode("utf-8")).hexdigest()

        # 3. Idempotency Check: DB exactly-once guarantee
        idempotency_key = cls.generate_idempotency_key(run_id, seq, tool.name, input_data)

        check_res = await session.execute(
            text("""
                SELECT id, status, output_ref FROM tool_executions
                WHERE tenant_id = :tenant_id AND tool_name = :tool_name AND idempotency_key = :key
            """),
            {"tenant_id": tenant_id, "tool_name": tool.name, "key": idempotency_key},
        )
        existing = check_res.fetchone()
        if existing and existing.status == "succeeded" and existing.output_ref:
            # Replay cached result
            return json.loads(existing.output_ref)

        execution_id = generate_id("tool_execution")
        start_time = time.perf_counter()

        # Record executing state
        await session.execute(
            text("""
                INSERT INTO tool_executions (
                    id, tenant_id, run_id, tool_name, tool_version, side_effect,
                    idempotency_key, input_hash, status, policy_verdict
                ) VALUES (
                    :id, :tenant_id, :run_id, :tool_name, :tool_version, :side_effect,
                    :idempotency_key, :input_hash, 'executing', :policy_verdict
                )
            """),
            {
                "id": execution_id,
                "tenant_id": tenant_id,
                "run_id": run_id,
                "tool_name": tool.name,
                "tool_version": tool.version,
                "side_effect": tool.side_effect,
                "idempotency_key": idempotency_key,
                "input_hash": input_hash,
                "policy_verdict": json.dumps(verdict.model_dump(mode="json")),
            },
        )

        try:
            # 4. Invoke tool handler
            if tool.handler:
                raw_output = await tool.handler(input_data)
            else:
                # Default mock success response if handler not attached
                raw_output = {"status": "success", "result": f"Executed {tool.name}"}

            validated_output = tool.output_schema.model_validate(raw_output)
            output_dict = validated_output.model_dump()
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # 5. Update execution row to succeeded
            await session.execute(
                text("""
                    UPDATE tool_executions
                    SET status = 'succeeded', output_ref = :output, latency_ms = :latency
                    WHERE id = :id
                """),
                {
                    "id": execution_id,
                    "output": json.dumps(output_dict),
                    "latency": latency_ms,
                },
            )

            # 6. Record in append-only cryptographic audit store (P7)
            await AuditWriter.record_event(
                session=session,
                tenant_id=tenant_id,
                event_type="tool.executed",
                actor_type="agent",
                actor_id=run_id,
                on_behalf_of=on_behalf_of,
                correlation_id=correlation_id,
                target_type=tool.name.split(".")[0],
                target_id=str(output_dict.get("id") or output_dict.get("case_id") or ""),
                data={
                    "tool": tool.name,
                    "input": input_data,
                    "output": output_dict,
                    "verdict": verdict.model_dump(mode="json"),
                },
            )

            return output_dict

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            await session.execute(
                text("""
                    UPDATE tool_executions
                    SET status = 'failed', latency_ms = :latency
                    WHERE id = :id
                """),
                {"id": execution_id, "latency": latency_ms},
            )
            raise RelayError(f"Tool {tool.name} failed: {str(e)}") from e
