"""Identity resolution engine enforcing strict non-auto-merge principles."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from relay.identity.models import CapabilityTier, IdentityCandidate, MatchBasis
from relay.platform.ids import generate_id


class IdentityResolver:
    """Resolves channel-specific IDs to unified contacts.
    
    Rules per §8.1:
    1. Channel-exact is the ONLY automatic match.
    2. Never auto-merge on weak signals (claimed email, fuzzy name).
    3. Merges are soft and reversible (contacts.merged_into).
    4. Capability tier gates access to account data and actions.
    """

    @staticmethod
    async def resolve_or_create(
        session: AsyncSession,
        tenant_id: str,
        channel: str,
        external_id: str,
        display_name: str | None = None,
        verified: bool = False,
    ) -> IdentityCandidate:
        """Resolve a contact identity or create a new contact record."""
        # 1. Check for exact channel identity match
        result = await session.execute(
            text("""
                SELECT ci.id, ci.contact_id, ci.verified, ci.confidence, ci.match_reason,
                       c.merged_into
                FROM contact_identities ci
                JOIN contacts c ON ci.contact_id = c.id
                WHERE ci.tenant_id = :tenant_id 
                  AND ci.channel = :channel 
                  AND ci.external_id = :external_id
            """),
            {
                "tenant_id": tenant_id,
                "channel": channel,
                "external_id": external_id,
            },
        )
        row = result.fetchone()

        if row:
            ci_id, contact_id, is_verified, confidence, match_reason, merged_into = row
            # Follow soft-merge pointer if present
            active_contact_id = merged_into if merged_into else contact_id
            tier = CapabilityTier.VERIFIED if is_verified else CapabilityTier.WEAK
            return IdentityCandidate(
                contact_id=active_contact_id,
                identity_id=ci_id,
                channel=channel,
                external_id=external_id,
                confidence=float(confidence),
                match_basis=MatchBasis(match_reason),
                tier=tier,
            )

        # 2. No exact match found -> Create new contact & identity
        contact_id = generate_id("contact")
        identity_id = generate_id("identity")

        await session.execute(
            text("""
                INSERT INTO contacts (id, tenant_id, display_name)
                VALUES (:id, :tenant_id, :display_name)
            """),
            {
                "id": contact_id,
                "tenant_id": tenant_id,
                "display_name": display_name,
            },
        )

        match_basis = MatchBasis.CHANNEL_EXACT
        tier = CapabilityTier.VERIFIED if verified else CapabilityTier.ANONYMOUS
        confidence = 1.0

        await session.execute(
            text("""
                INSERT INTO contact_identities (
                    id, tenant_id, contact_id, channel, external_id,
                    verified, confidence, match_reason
                ) VALUES (
                    :id, :tenant_id, :contact_id, :channel, :external_id,
                    :verified, :confidence, :match_reason
                )
            """),
            {
                "id": identity_id,
                "tenant_id": tenant_id,
                "contact_id": contact_id,
                "channel": channel,
                "external_id": external_id,
                "verified": verified,
                "confidence": confidence,
                "match_reason": match_basis.value,
            },
        )

        return IdentityCandidate(
            contact_id=contact_id,
            identity_id=identity_id,
            channel=channel,
            external_id=external_id,
            confidence=confidence,
            match_basis=match_basis,
            tier=tier,
        )

    @staticmethod
    async def soft_merge_contacts(
        session: AsyncSession,
        tenant_id: str,
        source_contact_id: str,
        target_contact_id: str,
    ) -> None:
        """Soft-merge one contact into another. Reversible support operation."""
        await session.execute(
            text("""
                UPDATE contacts 
                SET merged_into = :target_id, updated_at = now()
                WHERE id = :source_id AND tenant_id = :tenant_id
            """),
            {
                "source_id": source_contact_id,
                "target_id": target_contact_id,
                "tenant_id": tenant_id,
            },
        )
