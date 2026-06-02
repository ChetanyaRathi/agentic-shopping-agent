"""Find candidate product URLs via Gemini's Google Search grounding."""
from google.genai import types

from shopping_agent.llm import _client as client
from shopping_agent.models import Constraints, Candidate
from shopping_agent.cost.accounting import METER

SEARCH_MODEL = "gemini-2.5-flash"   # grounding needs a capable model


def discover(constraints: Constraints, max_candidates: int = 25) -> list[Candidate]:
    query = constraints.product
    if constraints.color:
        query += f" {constraints.color}"
    if constraints.price_max:
        query += f" under ${constraints.price_max:g}"

    resp = client.models.generate_content(
        model=SEARCH_MODEL,
        contents=f"Find specific online product pages to buy: {query}. "
                 "Return a wide variety of e-commerce sites, including marketplaces like eBay, Poshmark, Mercari, and independent stores. "
                 "Prefer direct product or listing pages from shopping sites.",
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    if resp.usage_metadata:
        METER.record(SEARCH_MODEL, resp.usage_metadata.prompt_token_count, resp.usage_metadata.candidates_token_count)

    candidates: list[Candidate] = []
    meta = resp.candidates[0].grounding_metadata if resp.candidates else None
    for ch in (getattr(meta, "grounding_chunks", None) or []):
        web = getattr(ch, "web", None)
        if web and web.uri:
            candidates.append(Candidate(url=web.uri, title_hint=web.title, source=web.title))
        if len(candidates) >= max_candidates:
            break
    return candidates
