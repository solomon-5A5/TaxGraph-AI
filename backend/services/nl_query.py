"""
NLQueryEngine — Convert natural language questions to Pandas operations
using Groq LLM. Returns query results + explanations.
"""

import os
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


class NLQueryEngine:
    """Natural language to Pandas query interface."""

    SCHEMA_DESCRIPTION = """Available DataFrames and their columns:
- taxpayers_df: gstin (str), legal_name (str), state_code (int), status (str: Active/Suspended/Cancelled), trust_score (float: 0.0-1.0)
- gstr1_df: invoice_id (str), supplier_gstin (str), receiver_gstin (str), invoice_date (str), total_value (float), tax_amount (float)
- gstr2b_df: invoice_id (str), receiver_gstin (str), supplier_gstin (str), total_value (float), itc_available (float)
- gstr3b_df: gstin (str), return_period (str), total_sales_declared (float), total_itc_claimed (float), tax_paid_cash (float)
- fraud_labels_df: gstin (str), is_fraud (int: 0 or 1), fraud_type (str)"""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key) if api_key else None

    def query(self, question: str, taxpayers_df: pd.DataFrame, gstr1_df: pd.DataFrame,
              gstr2b_df: pd.DataFrame, gstr3b_df: pd.DataFrame,
              fraud_labels_df: pd.DataFrame) -> dict:
        """Process a natural language query and return results."""
        if not self.client:
            return {
                "query": "",
                "results": [],
                "explanation": "LLM service unavailable. Please set GROQ_API_KEY.",
                "error": True,
            }

        # Generate Pandas code from question
        code = self._generate_code(question)

        if not code:
            return {
                "query": "",
                "results": [],
                "explanation": "Could not generate a valid query for your question.",
                "error": True,
            }

        # Execute in sandboxed namespace
        try:
            namespace = {
                "pd": pd,
                "taxpayers_df": taxpayers_df,
                "gstr1_df": gstr1_df,
                "gstr2b_df": gstr2b_df,
                "gstr3b_df": gstr3b_df,
                "fraud_labels_df": fraud_labels_df,
            }
            exec(code, namespace)
            result = namespace.get("result", pd.DataFrame())

            if isinstance(result, pd.DataFrame):
                # Limit to 100 rows for safety
                result_list = result.head(100).to_dict("records")
                # Convert any non-serializable types
                for row in result_list:
                    for key, value in row.items():
                        if pd.isna(value):
                            row[key] = None
                        elif hasattr(value, "item"):
                            row[key] = value.item()
            elif isinstance(result, pd.Series):
                result_list = result.head(100).to_dict()
                result_list = [{"key": k, "value": v} for k, v in result_list.items()]
            else:
                result_list = [{"result": str(result)}]

            # Generate explanation
            explanation = self._explain_results(question, result_list)

            return {
                "query": code,
                "results": result_list,
                "row_count": len(result_list),
                "explanation": explanation,
                "error": False,
            }

        except Exception as e:
            return {
                "query": code,
                "results": [],
                "explanation": f"Query execution error: {str(e)}",
                "error": True,
            }

    def _generate_code(self, question: str) -> str:
        """Use Groq to convert a question to Pandas code."""
        prompt = f"""You are a Python data analyst. Convert the user's question into
a Pandas query that runs against these DataFrames:

{self.SCHEMA_DESCRIPTION}

User question: "{question}"

RULES:
1. Return ONLY valid Python code. No markdown, no explanations.
2. Use variable name `result` for the final output DataFrame.
3. Do NOT import anything — pd is already available.
4. Do NOT use print() or display(). Just assign to `result`.
5. Handle potential missing columns gracefully.
6. Keep the code simple and safe — no file I/O, no network calls.
7. Values are in Indian Rupees (₹). "lakhs" = 100000, "crores" = 10000000.

Example: "Show invoices above 5 lakhs"
result = gstr1_df[gstr1_df["total_value"] > 500000]
"""

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a Python code generator. Return ONLY executable Python code, nothing else."},
                    {"role": "user", "content": prompt},
                ],
                model="llama-3.3-70b-versatile",
                max_tokens=500,
                temperature=0.1,
            )
            code = response.choices[0].message.content.strip()

            # Clean up markdown code fences if present
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
            code = code.strip()

            # Basic safety check
            dangerous_keywords = ["import os", "import sys", "subprocess", "open(", "__", "eval(", "exec(", "shutil"]
            for keyword in dangerous_keywords:
                if keyword in code:
                    return ""

            return code

        except Exception as e:
            print(f"⚠️ Groq code generation error: {e}")
            return ""

    def _explain_results(self, question: str, results: list) -> str:
        """Generate a natural language explanation of the results."""
        if not results:
            return "No results found for your query."

        if not self.client:
            return f"Found {len(results)} results."

        summary = f"Question: {question}\nResults: {len(results)} rows found."
        if len(results) <= 5:
            summary += f"\nData: {results}"

        prompt = (
            "You are a GST data analyst. The user asked a question and got results. "
            "Provide a brief 1-2 sentence summary of what the data shows.\n\n"
            f"{summary}\n\n"
            "Be concise and mention key numbers."
        )

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a concise data analyst."},
                    {"role": "user", "content": prompt},
                ],
                model="llama-3.3-70b-versatile",
                max_tokens=150,
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception:
            return f"Found {len(results)} results for your query."
