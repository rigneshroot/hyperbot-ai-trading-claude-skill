import os
import json
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Load env variables
load_dotenv()

class LlmMetaFilter:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        # Check if the key is a valid key (not a placeholder)
        self.is_active = bool(self.api_key and "your_anthropic_api_key" not in self.api_key and len(self.api_key) > 20)
        
        if self.is_active:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize Anthropic client: {str(e)}. Falling back to pass-through mode.")
                self.is_active = False

    def filter_signal(
        self, 
        symbol: str,
        side: str, 
        entry: float, 
        sl: float, 
        tp: float, 
        strategy_signals: dict,
        agree_count: int,
        recent_outcomes: List[str] = None
    ) -> Tuple[bool, str, str]:
        """
        Uses Claude API to reason about whether a mechanical signal should be approved.
        Returns:
            approve: bool (True to proceed, False to block)
            confidence: str ('high', 'medium', 'low')
            reason: str (Claude's reasoning)
        """
        if not self.is_active:
            msg = "[LLM FILTER DRY RUN] Claude API key is not configured or inactive. Automatically passing through."
            print(msg)
            return True, "high", msg

        # Construct a detailed prompt with the technical data
        strategy_data_str = ""
        for name, sig in strategy_signals.items():
            clean_name = name.replace("_", " ").title()
            strategy_data_str += f"- {clean_name}:\n"
            strategy_data_str += f"  Buy Confidence:  {sig.buy_confidence}%\n"
            strategy_data_str += f"  Sell Confidence: {sig.sell_confidence}%\n"
            strategy_data_str += f"  Regime:          {sig.regime}\n"
            strategy_data_str += f"  Reason:          {sig.reason}\n\n"

        outcomes_str = ", ".join(recent_outcomes) if recent_outcomes else "No recent trades recorded."

        system_prompt = (
            "You are a sophisticated risk management system for a professional quant trading bot. "
            "Your sole objective is to audit technical trading signals and decide whether to approve "
            "or reject them. You CANNOT create new signals; you can only REJECT mechanically triggered setups "
            "if you find structural discrepancies, conflicting regimes, stale levels, or signs of low probability. "
            "Respond strictly in valid JSON format: {\"approve\": true/false, \"confidence\": \"high/medium/low\", \"reason\": \"...\"}."
        )

        user_content = (
            f"Please audit the following proposed trade:\n\n"
            f"**Asset:** {symbol}\n"
            f"**Proposed Side:** {side.upper()}\n"
            f"**Entry Price:** {entry:.5f}\n"
            f"**Stop-Loss:** {sl:.5f}\n"
            f"**Take-Profit:** {tp:.5f}\n"
            f"**Agreement Count:** {agree_count}/5 strategies met the threshold.\n\n"
            f"**Recent Trade Outcomes:** {outcomes_str}\n\n"
            f"**Individual Strategy Output Context:**\n"
            f"{strategy_data_str}"
            f"Verify if there is a conflict. For example, check if Bollinger Band Squeeze "
            f"is screaming volatility breakout while MACD is signaling stalling momentum, "
            f"or if a Fair Value Gap is stale, or if the EMA Trend Pullback lacks HTF alignment. "
            f"Ensure your output is strictly a drop-in JSON block matching the specified format."
        )

        try:
            # Query Anthropic Claude 3.5 Sonnet / Haiku
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                temperature=0.0,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_content}
                ]
            )
            
            response_text = response.content[0].text.strip()
            
            # Locate the JSON block inside the text in case Claude adds markdown syntax
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(response_text)
            
            approve = bool(parsed.get("approve", False))
            confidence = str(parsed.get("confidence", "low")).lower()
            reason = str(parsed.get("reason", "No reason provided by LLM."))
            
            # Print audit detail
            print(f"\n--- Claude LLM Audit Verdict: {'[APPROVED]' if approve else '[REJECTED]'} ({confidence.upper()} confidence) ---")
            print(f"Reason: {reason}")
            print(f"--------------------------------------------------------------------------------\n")
            
            return approve, confidence, reason

        except Exception as e:
            # In case of API limits or server errors, pass through with high warnings
            err_msg = f"LLM Meta-Filter API Error: {str(e)}. Safely passing through to prevent trading interruption."
            print(f"WARNING: {err_msg}")
            return True, "high", err_msg
