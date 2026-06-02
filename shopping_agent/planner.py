"""Turn a natural-language shopping request into structured Constraints."""
from shopping_agent.llm import generate_structured
from shopping_agent.models import Constraints

PROMPT = """Convert this shopping request into structured search constraints.
Extract the product type, min/max price (numbers only), desired color, and how many
results the user wants (default 6 if unspecified).

REQUEST: {query}
"""


def plan(query: str) -> Constraints:
    return generate_structured(PROMPT.format(query=query), Constraints)
