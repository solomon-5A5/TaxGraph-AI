"""
ExplainableAIService — Generate human-readable explanations for
mismatches and risk decisions using template + Groq LLM.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


class ExplainableAIService:
    """Generates natural-language explanations for audit findings."""

    TEMPLATES = {
        "MISSING_IN_GSTR1": (
            "Invoice {invoice_id} (₹{gstr2b_value:,.2f}) appears in the buyer's "
            "GSTR-2B but is MISSING from the seller's ({supplier_gstin}) GSTR-1 "
            "filing. This means the seller either did not report this sale, filed "
            "late, or the invoice may be fabricated. The buyer's ITC claim is at "
            "risk until the seller files."
        ),
        "MISSING_IN_GSTR2B": (
            "Invoice {invoice_id} (₹{gstr1_value:,.2f}) was filed by the seller "
            "({supplier_gstin}) in GSTR-1 but has no corresponding entry in the "
            "buyer's ({receiver_gstin}) GSTR-2B. This is a phantom invoice — the "
            "buyer has not received or acknowledged this supply."
        ),
        "VALUE_MISMATCH": (
            "Invoice {invoice_id} shows ₹{gstr1_value:,.2f} in GSTR-1 but "
            "₹{gstr2b_value:,.2f} in GSTR-2B. The difference of "
            "₹{value_difference:,.2f} may indicate data entry errors, amended "
            "invoices, or deliberate manipulation."
        ),
        "TAX_MISMATCH": (
            "Invoice {invoice_id} has a tax amount discrepancy between GSTR-1 "
            "and GSTR-2B. The tax declared by the seller does not match the ITC "
            "available to the buyer, resulting in a revenue leakage risk."
        ),
        "CIRCULAR_TRADING": (
            "A circular trading pattern was detected involving {chain_length} "
            "entities: {chain_str}. Total circular value: {formatted_value}. "
            "This pattern is commonly associated with fake invoice rings used to "
            "inflate Input Tax Credit claims."
        ),
        "SHELL_COMPANY": (
            "Entity {gstin} has abnormally low network importance (PageRank: "
            "{pagerank}) but extremely high transaction volume ({formatted_volume}). "
            "This is a classic shell company pattern — a front entity used to "
            "route fake invoices through the network."
        ),
    }

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key) if api_key else None

    def explain_mismatch(self, mismatch: dict) -> dict:
        """Generate explanation for a reconciliation mismatch."""
        status = mismatch.get("status", "UNKNOWN")
        template = self.TEMPLATES.get(status, "")

        # Build base explanation from template
        try:
            base_explanation = template.format(**mismatch)
        except (KeyError, ValueError):
            base_explanation = f"Mismatch detected: {status} for invoice {mismatch.get('invoice_id', 'N/A')}"

        # Enhance with LLM if available
        enhanced = self._enhance_with_llm(
            base_explanation,
            context=f"Mismatch type: {status}, Severity: {mismatch.get('severity', 'N/A')}",
        )

        return {
            "invoice_id": mismatch.get("invoice_id", "N/A"),
            "status": status,
            "summary": base_explanation,
            "detailed_explanation": enhanced,
            "recommended_actions": self._get_actions(status),
            "severity": mismatch.get("severity", "INFO"),
        }

    def explain_risk(self, risk_data: dict) -> dict:
        """Generate explanation for a vendor's risk score."""
        gstin = risk_data.get("gstin", "Unknown")
        score = risk_data.get("risk_score", 0)
        level = risk_data.get("risk_level", "LOW")
        features = risk_data.get("features", {})

        # Build factor summary
        factors = []
        if features.get("is_known_fraud") == 1:
            factors.append(f"Known fraud label: {features.get('fraud_type', 'N/A')}")
        if features.get("zero_cash_tax_months", 0) >= 1:
            factors.append(f"{features['zero_cash_tax_months']} months with ₹0 cash tax paid")
        if features.get("itc_to_sales_ratio", 0) > 0.5:
            factors.append(f"High ITC-to-sales ratio: {features['itc_to_sales_ratio']:.2f}")
        if features.get("pagerank_score", 0) < 0.005 and features.get("total_outward_value", 0) > 5000000:
            factors.append("Low network importance but high transaction volume (shell company pattern)")

        base_explanation = (
            f"Vendor {gstin} has a risk score of {score:.2f} ({level}). "
            f"Key risk factors: {'; '.join(factors) if factors else 'No specific risk factors identified.'}"
        )

        enhanced = self._enhance_with_llm(
            base_explanation,
            context=f"Risk level: {level}, Score: {score}",
        )

        return {
            "gstin": gstin,
            "risk_score": score,
            "risk_level": level,
            "summary": base_explanation,
            "detailed_explanation": enhanced,
            "key_factors": factors,
        }

    def explain_fraud_pattern(self, pattern_type: str, pattern_data: dict) -> dict:
        """Generate explanation for a detected fraud pattern."""
        template = self.TEMPLATES.get(pattern_type, "")

        try:
            base_explanation = template.format(**pattern_data)
        except (KeyError, ValueError):
            base_explanation = f"Fraud pattern detected: {pattern_type}"

        enhanced = self._enhance_with_llm(
            base_explanation,
            context=f"Pattern type: {pattern_type}",
        )

        return {
            "pattern_type": pattern_type,
            "summary": base_explanation,
            "detailed_explanation": enhanced,
            "severity": "CRITICAL",
        }

    def _enhance_with_llm(self, base_explanation: str, context: str) -> str:
        """Enhance explanation using Groq LLM."""
        if not self.client:
            return base_explanation

        prompt = (
            "You are an expert GST Intelligence Officer in India. Given this finding, "
            "provide a clear, actionable 2-3 sentence explanation for a tax officer:\n\n"
            f"Finding: {base_explanation}\n"
            f"Context: {context}\n\n"
            "Explain: (1) What happened, (2) Why it matters, (3) What action to take. "
            "Be concise and professional."
        )

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert GST Intelligence Officer."},
                    {"role": "user", "content": prompt},
                ],
                model="llama-3.3-70b-versatile",
                max_tokens=300,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ Groq LLM error: {e}")
            return base_explanation

    def _get_actions(self, status: str) -> list[str]:
        """Get recommended actions for a given mismatch type."""
        actions = {
            "MISSING_IN_GSTR1": [
                "Issue notice to seller to file amended GSTR-1",
                "Suspend buyer's ITC claim until seller files",
                "Add seller to watchlist for late filing",
            ],
            "MISSING_IN_GSTR2B": [
                "Verify if buyer received the goods/services",
                "Check for potential phantom invoice creation",
                "Cross-check with e-way bill records",
            ],
            "VALUE_MISMATCH": [
                "Request both parties to submit original invoices",
                "Check for credit/debit notes that may explain the difference",
                "Flag for manual audit if difference exceeds ₹1 lakh",
            ],
            "TAX_MISMATCH": [
                "Verify HSN code classification for correct tax rate",
                "Check if partial ITC reversal is required",
                "Cross-reference with GSTR-9 annual return",
            ],
        }
        return actions.get(status, ["Refer to senior officer for manual review"])
