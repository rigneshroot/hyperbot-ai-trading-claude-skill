"""
institutional_context.py
------------------------
Provides macro-level institutional positioning context alongside
technical trade setups.

Designed as an ecosystem bridge to institutional-finance-skills.
A compliant institutional-finance-skills instance can inject live
sector flow data directly into the InstitutionalContextProvider.

In standalone mode (no live data feed), returns structured
placeholder context with clear extension points documented.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Static sector context definitions (extension point for live data feeds)
# ---------------------------------------------------------------------------

# This dict mirrors the sector taxonomy used in institutional-finance-skills.
# Replace or extend values with live 13F / flow data from that repo.
SECTOR_CONTEXT_STUBS: Dict[str, dict] = {
    "BTC": {
        "sector": "Digital Assets",
        "institutional_flow": "neutral",
        "recent_signal": (
            "Spot ETF inflows have stabilised. Major custodians report flat "
            "allocation changes over the past 30 days. No clear institutional "
            "accumulation or distribution signal at this time."
        ),
        "macro_tailwind": None,
        "macro_headwind": "Elevated short-term interest rates reduce speculative risk appetite.",
        "source": "institutional-finance-skills / digital-asset-flows [stub]",
    },
    "ETH": {
        "sector": "Digital Assets / Smart Contract Platforms",
        "institutional_flow": "mild_accumulation",
        "recent_signal": (
            "Ethereum staking inflows from institutional custodians remain elevated. "
            "Several large asset managers have increased ETH exposure in recent quarters."
        ),
        "macro_tailwind": "DeFi infrastructure narrative supports medium-term institutional interest.",
        "macro_headwind": None,
        "source": "institutional-finance-skills / digital-asset-flows [stub]",
    },
    "SOL": {
        "sector": "Digital Assets / Layer 1",
        "institutional_flow": "neutral",
        "recent_signal": (
            "No significant 13F-equivalent disclosure changes in SOL-adjacent funds. "
            "Retail-driven asset at this stage."
        ),
        "macro_tailwind": None,
        "macro_headwind": None,
        "source": "institutional-finance-skills / digital-asset-flows [stub]",
    },
}

DEFAULT_CONTEXT = {
    "sector": "Unknown",
    "institutional_flow": "unknown",
    "recent_signal": (
        "No institutional context available for this asset. "
        "Extend SECTOR_CONTEXT_STUBS with live data from institutional-finance-skills."
    ),
    "macro_tailwind": None,
    "macro_headwind": None,
    "source": "institutional-finance-skills [stub — no live feed configured]",
}


@dataclass
class InstitutionalContext:
    """
    Structured macro-level institutional context for a symbol.
    """
    symbol: str
    sector: str
    institutional_flow: str          # 'accumulation', 'distribution', 'neutral', etc.
    recent_signal: str
    macro_tailwind: Optional[str]
    macro_headwind: Optional[str]
    source: str
    live_feed_active: bool = False   # True when connected to institutional-finance-skills

    def display(self) -> str:
        lines = [
            "\nInstitutional Context:",
            "-" * 50,
            f"Asset:               {self.symbol}",
            f"Sector:              {self.sector}",
            f"Institutional Flow:  {self.institutional_flow.replace('_', ' ').title()}",
            f"Signal:              {self.recent_signal}",
        ]
        if self.macro_tailwind:
            lines.append(f"Macro Tailwind:      {self.macro_tailwind}")
        if self.macro_headwind:
            lines.append(f"Macro Headwind:      {self.macro_headwind}")
        lines += [
            f"Source:              {self.source}",
            f"Live Feed:           {'Active' if self.live_feed_active else 'Stub mode — see institutional-finance-skills'}",
            "-" * 50,
        ]
        return "\n".join(lines)

    def alignment_note(self, direction: str) -> str:
        """
        Returns a short one-liner on whether institutional flow
        aligns with the proposed trade direction.
        """
        flow = self.institutional_flow
        if direction == "long":
            if flow == "accumulation":
                return "Institutional flow aligns with long setup (accumulation detected)."
            elif flow == "distribution":
                return "Caution: Institutional flow diverges from long setup (distribution detected)."
            else:
                return "Institutional flow is neutral — no directional conviction from institutional participants."
        elif direction == "short":
            if flow == "distribution":
                return "Institutional flow aligns with short setup (distribution detected)."
            elif flow == "accumulation":
                return "Caution: Institutional flow diverges from short setup (accumulation detected)."
            else:
                return "Institutional flow is neutral — no directional conviction from institutional participants."
        return "No institutional alignment assessment available."


class InstitutionalContextProvider:
    """
    Provides macro institutional positioning context for a given symbol.

    Extension points
    ----------------
    To connect live data from institutional-finance-skills, subclass
    this provider and override the `_fetch_live_context` method.

    Example:
        class LiveProvider(InstitutionalContextProvider):
            def _fetch_live_context(self, symbol: str) -> dict:
                return institutional_finance_skills.get_flow(symbol)
    """

    def __init__(self, live_feed: Optional[dict] = None):
        """
        Parameters
        ----------
        live_feed : Optional dict mapping symbol -> context dict.
                    Injected by institutional-finance-skills when active.
        """
        self.live_feed = live_feed or {}

    def get_context(self, symbol: str) -> InstitutionalContext:
        """Returns institutional context for a given symbol."""
        symbol_upper = symbol.upper()

        # Priority: live feed > stubs > default
        if symbol_upper in self.live_feed:
            raw = self.live_feed[symbol_upper]
            live = True
        elif symbol_upper in SECTOR_CONTEXT_STUBS:
            raw = SECTOR_CONTEXT_STUBS[symbol_upper]
            live = False
        else:
            raw = DEFAULT_CONTEXT
            live = False

        return InstitutionalContext(
            symbol=symbol_upper,
            sector=raw.get("sector", "Unknown"),
            institutional_flow=raw.get("institutional_flow", "unknown"),
            recent_signal=raw.get("recent_signal", ""),
            macro_tailwind=raw.get("macro_tailwind"),
            macro_headwind=raw.get("macro_headwind"),
            source=raw.get("source", "institutional-finance-skills [stub]"),
            live_feed_active=live,
        )
