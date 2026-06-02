"""Drop products that violate the hard constraints."""
from shopping_agent.models import Product, Constraints


def passes(p: Product, c: Constraints) -> bool:
    if p.price is None:
        return False                       # couldn't read a price → useless
    if c.price_min is not None and p.price < c.price_min:
        return False
    if c.price_max is not None and p.price > c.price_max:
        return False
    if p.in_stock is False:
        return False
    if c.color and p.color:                # only drop on an EXPLICIT colour mismatch
        if c.color.lower() not in p.color.lower() and p.color.lower() not in c.color.lower():
            return False
            
    # Simple relevance check: at least one core keyword from the product constraint must be in the title
    keywords = [k.lower() for k in c.product.split() if len(k) > 2]
    if keywords:
        title_lower = p.title.lower()
        if not any(k in title_lower for k in keywords):
            return False
            
    return True                            # unknown colour is kept; ranker deprioritises it
