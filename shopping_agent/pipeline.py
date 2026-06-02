"""End to end: query -> constraints -> candidates -> extract -> filter -> rank -> top N."""
from shopping_agent.planner import plan
from shopping_agent.discovery import discover
from shopping_agent.extract.worker import harvest
from shopping_agent.rank.filter import passes
from shopping_agent.rank.ranker import score
from shopping_agent.mcp_client.connection import PlaywrightMCP
from shopping_agent.mcp_client.tools import call, result_image
from shopping_agent.models import RankedResult, Candidate
from shopping_agent.cost.accounting import METER, BudgetExceeded
from shopping_agent.extract.color import confirm_color_vision


async def run_stream(query: str, headless: bool = True, seed_urls=None, verbose: bool = True, budget: float = 0.10):
    METER.reset(budget)
    ranked = []
    
    try:
        constraints = plan(query)
        candidates = [Candidate(url=u) for u in seed_urls] if seed_urls else discover(constraints)
        if verbose:
            print(f"Constraints: {constraints.model_dump()}")
            print(f"Using {len(candidates)} candidates. Visiting...\n")

        products = []
        async with PlaywrightMCP(headless=headless) as mcp:
            for i, cand in enumerate(candidates, 1):
                try:
                    constraints_str = constraints.model_dump_json(exclude_none=True)
                    found = await harvest(mcp.session, cand.url, max_children=12, constraints_str=constraints_str)
                    
                    for p in found:
                        if passes(p, constraints):
                            products.append(p)
                            r = RankedResult(product=p, score=score(p, constraints))
                            ranked.append(r)
                            yield {"type": "product", "data": r}

                    if verbose:
                        print(f"  [{i}/{len(candidates)}] {(cand.title_hint or cand.url)[:30]}: +{len(found)}")
                except BudgetExceeded as e:
                    if verbose:
                        print(f"\n[!] {e}")
                    raise  # bubble to outer try/except
                except Exception as e:
                    if verbose:
                        print(f"  [{i}/{len(candidates)}] FAIL {type(e).__name__}")

            ranked = sorted(ranked, key=lambda r: r.score, reverse=True)
            
            # Vision Fallback for top candidates
            if constraints.color:
                for r in ranked[:6]:
                    if not r.product.color:
                        try:
                            await call(mcp.session, "browser_navigate", url=r.product.url)
                            snap = await call(mcp.session, "browser_take_screenshot")
                            img_data = result_image(snap)
                            if img_data:
                                b64, mime = img_data
                                is_match = confirm_color_vision(b64, mime, constraints.color)
                                if is_match:
                                    r.score += 0.5
                                    r.product.color = constraints.color
                        except BudgetExceeded as e:
                            if verbose:
                                print(f"\n[!] {e}")
                            raise  # bubble out
                        except Exception:
                            pass
                            
                ranked = sorted(ranked, key=lambda r: r.score, reverse=True)
                
            ranked = ranked[:constraints.count]
            if verbose:
                print(f"\nExtracted {len(products)} · passed filter {len(ranked)} · top {len(ranked)}")

    except BudgetExceeded as e:
        print(f"\nBudget cap hit: {e}")
        
    yield {"type": "done", "ranked": ranked, "cost_report": METER.report()}


async def run(query: str, headless: bool = True, seed_urls=None, verbose: bool = True, budget: float = 0.10):
    final_ranked = []
    final_cost = {}
    async for event in run_stream(query, headless, seed_urls, verbose, budget):
        if event["type"] == "done":
            final_ranked = event["ranked"]
            final_cost = event["cost_report"]
    return final_ranked, final_cost
