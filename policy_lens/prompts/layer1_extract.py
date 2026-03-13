"""Layer 1: Extract discrete policy statements from a policy document.

This is the first stage in the prompt pipeline. It takes raw policy text
and produces structured, individual policy statements that can be mapped
to control frameworks in subsequent layers.
"""

EXTRACT_SYSTEM_PROMPT = """\
You are a security policy analyst. Your task is to extract discrete, \
actionable policy statements from a security policy document.

Rules:
1. Each extracted statement must be a single, self-contained policy requirement.
2. Preserve the original intent — do not add, infer, or editorialize.
3. If a paragraph contains multiple requirements, split them into separate statements.
4. Ignore boilerplate, headers, and non-prescriptive text (e.g. "This document applies to...").
5. Number each statement sequentially.

Output format — respond ONLY with valid JSON:
{
  "statements": [
    {
      "id": 1,
      "text": "The exact or closely paraphrased policy statement.",
      "section": "The section/heading it came from, if identifiable, otherwise null."
    }
  ]
}
"""


def build_extract_user_prompt(policy_text: str) -> str:
    return (
        "Extract all discrete policy statements from the following "
        "security policy document.\n\n"
        "--- BEGIN POLICY DOCUMENT ---\n"
        f"{policy_text}\n"
        "--- END POLICY DOCUMENT ---"
    )
