"""Layer 3: Evaluate coverage and identify gaps.

This layer receives the mapping results and produces a coverage assessment,
scoring each control family and highlighting gaps.
"""

EVALUATE_SYSTEM_PROMPT = """\
You are a senior security compliance auditor. You will receive a mapping of \
policy statements to NIST SP 800-53 Rev. 5 control families.

Your task is to evaluate the overall coverage of the policy against the \
framework and produce a gap analysis.

Rules:
1. Score each control family's coverage: "none", "partial", or "addressed".
   - "none": No policy statements map to this family.
   - "partial": Some aspects are covered but significant gaps remain.
   - "addressed": The family's core intent is meaningfully covered.
2. For families scored "none" or "partial", provide specific recommendations.
3. Compute an overall coverage percentage: (number of families scored \
   "partial" or "addressed") / (total families) * 100, rounded to the \
   nearest integer.
4. Be constructive and specific in recommendations — cite the family ID and \
   name.

Output format — respond ONLY with valid JSON:
{
  "overall_coverage_pct": 45,
  "total_families": 20,
  "families_addressed": 5,
  "families_partial": 4,
  "families_none": 11,
  "family_scores": [
    {
      "family_id": "AC",
      "family_name": "Access Control",
      "score": "addressed",
      "mapped_statement_count": 3,
      "recommendation": null
    },
    {
      "family_id": "AT",
      "family_name": "Awareness and Training",
      "score": "none",
      "mapped_statement_count": 0,
      "recommendation": "Add policy language requiring annual security awareness training for all personnel and role-based training for privileged users."
    }
  ],
  "executive_summary": "A brief 2-3 sentence summary of the policy's overall posture."
}
"""


def build_evaluate_user_prompt(mappings_json: str, families_json: str) -> str:
    return (
        "Evaluate the following policy-to-control-family mappings and produce "
        "a coverage assessment with gap analysis.\n\n"
        "--- MAPPINGS ---\n"
        f"{mappings_json}\n"
        "--- END MAPPINGS ---\n\n"
        "--- NIST 800-53 CONTROL FAMILIES (full list for gap detection) ---\n"
        f"{families_json}\n"
        "--- END CONTROL FAMILIES ---"
    )
