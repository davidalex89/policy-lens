"""Layer 3: Evaluate coverage and identify gaps.

This layer receives the mapping results and produces a coverage assessment,
scoring each control family and highlighting gaps.
"""

def build_evaluate_system_prompt(
    framework_name: str = "the selected security framework",
) -> str:
    return (
        f"You are a senior security compliance auditor. You will receive a mapping of "
        f"policy statements to {framework_name} control families.\n\n"
        "Your task is to evaluate the overall coverage of the policy against the "
        "framework and produce a gap analysis.\n\n"
        'Rules:\n'
        '1. Score each control family\'s coverage: "none", "partial", or "addressed".\n'
        '   - "none": No policy statements map to this family.\n'
        '   - "partial": Some aspects are covered but significant gaps remain.\n'
        '   - "addressed": The family\'s core intent is meaningfully covered.\n'
        '2. For families scored "none" or "partial", provide specific recommendations.\n'
        "3. Compute an overall coverage percentage: (number of families scored "
        '"partial" or "addressed") / (total families) * 100, rounded to the '
        "nearest integer.\n"
        "4. Be constructive and specific in recommendations — cite the family ID and "
        "name.\n\n"
        "Output format — respond ONLY with valid JSON:\n"
        "{\n"
        '  "overall_coverage_pct": 45,\n'
        '  "total_families": 20,\n'
        '  "families_addressed": 5,\n'
        '  "families_partial": 4,\n'
        '  "families_none": 11,\n'
        '  "family_scores": [\n'
        "    {\n"
        '      "family_id": "AC",\n'
        '      "family_name": "Access Control",\n'
        '      "score": "addressed",\n'
        '      "mapped_statement_count": 3,\n'
        '      "recommendation": null\n'
        "    },\n"
        "    {\n"
        '      "family_id": "AT",\n'
        '      "family_name": "Awareness and Training",\n'
        '      "score": "none",\n'
        '      "mapped_statement_count": 0,\n'
        '      "recommendation": "Add policy language requiring annual security awareness training for all personnel and role-based training for privileged users."\n'
        "    }\n"
        "  ],\n"
        '  "executive_summary": "A brief 2-3 sentence summary of the policy\'s overall posture."\n'
        "}"
    )


def build_evaluate_user_prompt(
    mappings_json: str,
    families_json: str,
    framework_name: str = "NIST SP 800-53 Rev. 5",
) -> str:
    return (
        "Evaluate the following policy-to-control-family mappings and produce "
        "a coverage assessment with gap analysis.\n\n"
        "--- MAPPINGS ---\n"
        f"{mappings_json}\n"
        "--- END MAPPINGS ---\n\n"
        f"--- {framework_name.upper()} CONTROL FAMILIES (full list for gap detection) ---\n"
        f"{families_json}\n"
        "--- END CONTROL FAMILIES ---"
    )
