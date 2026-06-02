"""Turn a candidate URL into one or more structured Products.

A candidate may be a single product page OR a listing/search page. If it's a
listing (no single price), pull its product links and extract each one.
"""
import re
import json
import httpx
from mcp import ClientSession
from difflib import SequenceMatcher

from shopping_agent.llm import generate_structured
from shopping_agent.models import Product, ExtractedProduct, ExtractedProductsList
from shopping_agent.mcp_client.tools import call, result_text

MAX_SNAPSHOT_CHARS = 6000
LISTING_SNAPSHOT_CHARS = 40000

PRODUCT_PROMPT = """Extract the product from this page accessibility snapshot.
Return title, price (number only), currency, color (ONLY if the text states it),
and in_stock. Use null for anything not present. Never guess colour.

PAGE URL: {url}

SNAPSHOT:
{snapshot}
"""

LISTING_PROMPT = """This may be a product listing or search-results page.
Extract up to {k} INDIVIDUAL products that match these CONSTRAINTS: {constraints_str}.
Return their title, price, currency, color (if stated), and in_stock status.
CRITICAL: If a constraint (like color) is not explicitly visible in the text snippet, assume it MIGHT match and include the product anyway!
If it is a single product page (not a listing of multiple products), return an empty list [].

SNAPSHOT:
{snapshot}
"""


async def _snapshot(session: ClientSession, url: str) -> str:
    await call(session, "browser_navigate", url=url)
    return result_text(await call(session, "browser_snapshot", depth=12))


def _page_url(snapshot: str, fallback: str) -> str:
    """Pull the resolved 'Page URL' from the snapshot header so we report real links."""
    for line in snapshot.splitlines():
        if "Page URL:" in line:
            return line.split("Page URL:", 1)[1].strip()
    return fallback


def _extract_one(snapshot: str, url: str) -> Product:
    ep: ExtractedProduct = generate_structured(PRODUCT_PROMPT.format(url=url, snapshot=snapshot[:MAX_SNAPSHOT_CHARS]), ExtractedProduct)
    real_url = _page_url(snapshot, url).split('?')[0]     # prefer the real resolved URL, clean query params
    return Product(**ep.model_dump(), url=real_url)


def _extract_listing(snapshot: str, k: int, constraints_str: str = "None") -> list[ExtractedProduct]:
    res: ExtractedProductsList = generate_structured(LISTING_PROMPT.format(k=k, constraints_str=constraints_str, snapshot=snapshot[:LISTING_SNAPSHOT_CHARS]), ExtractedProductsList)
    return res.products[:k]


def _best_match_url(title: str, anchors: list[dict], base_url: str) -> str | None:
    best_score = 0.0
    best_href = None
    
    title_lower = title.lower()
    for a in anchors:
        text_lower = a.get("text", "").lower()
        if not text_lower:
            continue
            
        score = SequenceMatcher(None, title_lower, text_lower).ratio()
        if title_lower in text_lower or text_lower in title_lower:
            score += 0.5
            
        if score > best_score:
            best_score = score
            best_href = a.get("href")
            
    if best_href and best_score > 0.3:
        if best_href.startswith("/"):
            from urllib.parse import urljoin
            return urljoin(base_url, best_href)
        return best_href
    return None


async def harvest(session: ClientSession, url: str, max_children: int = 6, constraints_str: str = "None") -> list[Product]:
    """Return product(s) from a candidate, expanding a listing one level deep."""
    snapshot = await _snapshot(session, url)
    real_page_url = _page_url(snapshot, url)
    
    extracted_items = _extract_listing(snapshot, max_children, constraints_str)
    
    if len(extracted_items) >= 2:
        js_code = """() => {
            return JSON.stringify(Array.from(document.querySelectorAll('a[href]'))
                .map(a => ({ text: a.innerText.trim(), href: a.href }))
                .filter(x => x.text && x.href.startsWith('http')))
        }"""
        eval_result = await call(session, "browser_evaluate", function=js_code)
        
        anchors = []
        if eval_result:
            try:
                raw = result_text(eval_result)
                match = re.search(r'### Result\n(.*?)\n###', raw, re.DOTALL)
                if match:
                    json_str = json.loads(match.group(1).strip())
                    if isinstance(json_str, str):
                        anchors = json.loads(json_str)
                    else:
                        anchors = json_str
            except Exception:
                pass

        products: list[Product] = []
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0"}
        async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
            for item in extracted_items:
                matched_url = _best_match_url(item.title, anchors, real_page_url)
                if not matched_url:
                    continue
                    
                # Verify URL works (HTTP < 400)
                try:
                    resp = await client.get(matched_url, follow_redirects=True)
                    if resp.status_code >= 400:
                        continue
                except Exception:
                    continue
                
                try:
                    child = _extract_one(await _snapshot(session, matched_url), matched_url)
                    if child.price is not None:
                        products.append(child)
                except Exception:
                    continue
        return products
    else:
        # Treat as a single product page
        product = _extract_one(snapshot, url)
        if product.price is not None:
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0"}
            async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                try:
                    resp = await client.get(product.url, follow_redirects=True)
                    if resp.status_code >= 400:
                        return []
                except Exception:
                    return []
            return [product]
        return []
