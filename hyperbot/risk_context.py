from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Risk Profile definitions
# ---------------------------------------------------------------------------

RISK_PROFILES = {
    "conservative": {
        "max_position_pct": 5.0,
        "max_daily_loss_pct": -2.0,
        "max_account_risk_per_trade_pct": 0.5,
        "min_rr_ratio": 2.5,
        "description": "Low exposure. Suitable for research and paper trading.",
    },
    "moderate": {
        "max_position_pct": 15.0,
        "max_daily_loss_pct": -4.0,
        "max_account_risk_per_trade_pct": 1.0,
        "min_rr_ratio": 2.0,
        "description": "Balanced exposure. Default research profile.",
    },
    "aggressive": {
        "max_position_pct": 25.0,
        "max_daily_loss_pct": -6.0,
        "max_account_risk_per_trade_pct": 2.0,
        "min_rr_ratio": 1.5,
        "description": "Higher exposure. Only suitable after extensive validation.",
    },
}


@dataclass
class RiskAssessment:
    """
    Outcome of evaluating a proposed trade against the active risk profile.
    """
    profile_name: str
    approved: bool
    adjusted_position_pct: float
    warnings: list
    rationale: str

    def display(self) -> str:
        status = "APPROVED" if self.approved else "FLAGGED"
        lines = [
            f"\nRisk Assessment [{self.profile_name.upper()} profile] — {status}",
            "-" * 50,
            f"Adjusted Position Size: {self.adjusted_position_pct:.1f}% of portfolio",
        ]
        if self.warnings:
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        lines.append(f"Rationale: {self.rationale}")
        lines.append("-" * 50)
        return "\n".join(lines)


class RiskContextLayer:
    """
    Applies a configurable risk tolerance profile to a proposed position.

    Designed to be interoperable with the ai-risk-copilot ecosystem schema.
    A compliant ai-risk-copilot instance can pass its active profile name
    and daily PnL state directly to this layer.

    Parameters
    ----------
    profile_name  : 'conservative', 'moderate', or 'aggressive'
    daily_pnl_pct : Current day's realised PnL percentage (negative = loss)
    """

    def __init__(self, profile_name: str = "moderate", daily_pnl_pct: float = 0.0):
        profile_name = profile_name.lower()
        if profile_name not in RISK_PROFILES:
            print(f"[RiskContext] Unknown profile '{profile_name}'. Defaulting to 'moderate'.")
            profile_name = "moderate"

        self.profile_name = profile_name
        self.profile = RISK_PROFILES[profile_name]
        self.daily_pnl_pct = daily_pnl_pct

    def evaluate(
        self,
        proposed_position_pct: float,
        risk_reward: float,
        confidence_score: int,
        strategies_agreed: int,
    ) -> RiskAssessment:
        """
        Evaluates a proposed trade against the active risk profile.

        Returns a RiskAssessment with an adjusted position size,
        any warnings raised, and a plain-language rationale.
        """
        warnings = []
        approved = True
        adjusted = proposed_position_pct

        # 1. Position size cap
        max_pos = self.profile["max_position_pct"]
        if proposed_position_pct > max_pos:
            warnings.append(
                f"Proposed size {proposed_position_pct:.1f}% exceeds "
                f"{self.profile_name} cap of {max_pos:.1f}%. Capped."
            )
            adjusted = max_pos

        # 2. Daily drawdown buffer check
        remaining_buffer = self.profile["max_daily_loss_pct"] - self.daily_pnl_pct
        if self.daily_pnl_pct <= self.profile["max_daily_loss_pct"]:
            warnings.append(
                f"Daily loss limit reached ({self.daily_pnl_pct:.2f}% vs "
                f"limit {self.profile['max_daily_loss_pct']:.2f}%). No new entries."
            )
            approved = False
            adjusted = 0.0

        # 3. Risk/reward minimum check
        min_rr = self.profile["min_rr_ratio"]
        if risk_reward < min_rr:
            warnings.append(
                f"Risk/Reward ratio 1:{risk_reward:.1f} is below {self.profile_name} "
                f"minimum of 1:{min_rr:.1f}."
            )
            approved = False

        # 4. Confidence floor — require at least 3/5 for any profile
        if strategies_agreed < 3:
            warnings.append(
                f"Only {strategies_agreed}/5 strategies agree. "
                "Minimum of 3/5 required regardless of risk profile."
            )
            approved = False

        # Compose rationale
        if approved:
            rationale = (
                f"Setup passes {self.profile_name} risk profile. "
                f"Adjusted to {adjusted:.1f}% position size. "
                f"Daily PnL buffer remaining: {remaining_buffer:.2f}%."
            )
        else:
            rationale = (
                f"Setup flagged under {self.profile_name} profile. "
                + " ".join(warnings)
            )

        return RiskAssessment(
            profile_name=self.profile_name,
            approved=approved,
            adjusted_position_pct=adjusted,
            warnings=warnings,
            rationale=rationale,
        )

    @staticmethod
    def list_profiles() -> str:
        lines = ["Available Risk Profiles:", "-" * 40]
        for name, p in RISK_PROFILES.items():
            lines.append(f"  {name:<12} — {p['description']}")
        return "\n".join(lines)
