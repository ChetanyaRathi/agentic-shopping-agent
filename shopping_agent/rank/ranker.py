"""Score the survivors so we can pick the best few."""
from shopping_agent.models import Product, Constraints


def score(p: Product, c: Constraints) -> float:
    s = 0.0
    if c.color and p.color and c.color.lower() in p.color.lower():
        s += 0.5                            # confirmed colour match
    elif c.color and not p.color:
        s += 0.1                            # colour unknown
    else:
        s += 0.3
    if p.price is not None and c.price_max:
        s += 0.3 * (1 - p.price / c.price_max)   # cheaper = slightly better
    if p.in_stock:
        s += 0.2
    return s
