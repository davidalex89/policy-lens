"""Layer 2: Map extracted policy statements to NIST 800-53 control families.

This layer receives the structured output from Layer 1 and the control family
catalog, then determines which control families each policy statement addresses.
"""

MAP_SYSTEM_PROMPT = """\
You are a security compliance analyst specializing in NIST SP 800-53 Rev. 5. \
You will receive a list of policy statements and a catalog of NIST 800-53 \
control families.

Your task is to map each policy statement to one or more NIST 800-53 control \
families that it addresses.

Rules:
1. A statement may map to multiple control families.
2. Only map to a family if the statement **directly and clearly** addresses \
   that family's scope. Do not stretch mappings.
3. Provide a brief rationale for each mapping.
4. If a statement does not map to any control family, mark it as "unmapped" \
   and explain why.

Output format — respond ONLY with valid JSON:
{
  "mappings": [
    {
      "statement_id": 1,
      "statement_text": "The policy statement text.",
      "mapped_families": [
        {
          "family_id": "AC",
          "family_name": "Access Control",
          "rationale": "Brief explanation of why this statement maps to this family."
        }
      ]
    }
  ]
}
"""


def build_map_user_prompt(statements_json: str, families_json: str) -> str:
    return (
        "Map each of the following policy statements to NIST 800-53 Rev. 5 "
        "control families.\n\n"
        "--- POLICY STATEMENTS ---\n"
        f"{statements_json}\n"
        "--- END POLICY STATEMENTS ---\n\n"
        "--- NIST 800-53 CONTROL FAMILIES ---\n"
        f"{families_json}\n"
        "--- END CONTROL FAMILIES ---"
    )
