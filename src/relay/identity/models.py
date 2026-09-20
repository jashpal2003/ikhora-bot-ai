"""Identity models, verification tiers, and capability definitions."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class CapabilityTier(str, Enum):
    """Tiered permissions unlocked by identity verification level."""

    ANONYMOUS = "anonymous"  # Public knowledge only. Zero account data.
    WEAK = "weak"  # Claimed email/phone without cryptographic/OTP proof.
    VERIFIED = "verified"  # Verified via OTP, OAuth subject, or Teams SSO.
    VERIFIED_POLICY = "verified_policy"  # Verified + explicitly authorized for financial/destructive actions.


class MatchBasis(str, Enum):
    """Basis on which identity match was established."""

    CHANNEL_EXACT = "channel_exact"  # Same WhatsApp E.164, same Teams OID.
    VERIFIED_OTP = "verified_otp"
    OAUTH_SUBJECT = "oauth_subject"
    CANDIDATE_LINK = "candidate_link"  # Requires human operator confirmation.
    NONE = "none"


class IdentityCandidate(BaseModel):
    """An identity match candidate."""

    contact_id: str
    identity_id: str
    channel: str
    external_id: str
    confidence: float
    match_basis: MatchBasis
    tier: CapabilityTier
    metadata: dict[str, Any] = Field(default_factory=dict)
