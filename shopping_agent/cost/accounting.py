"""Token counting and cost tracking for Gemini API usage."""

class BudgetExceeded(BaseException):
    """Raised when the cost cap is hit."""
    pass

# Rates in USD per 1,000,000 tokens (input, output)
RATES = {
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.00),
}


class CostMeter:
    def __init__(self):
        self.budget: float = 0.10
        self.total_usd: float = 0.0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.calls: int = 0
        self.model_calls: dict[str, int] = {}

    def reset(self, budget: float = 0.10):
        """Reset the meter with a new budget."""
        self.budget = budget
        self.total_usd = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.calls = 0
        self.model_calls = {}

    def record(self, model: str, in_tok: int, out_tok: int):
        """Record a Gemini call and check against the budget."""
        # Find closest model match if the exact string differs (e.g., has a suffix)
        rate_key = model
        if rate_key not in RATES:
            for k in RATES:
                if k in model:
                    rate_key = k
                    break
        
        in_rate, out_rate = RATES.get(rate_key, (0.0, 0.0))
        call_cost = (in_tok / 1_000_000 * in_rate) + (out_tok / 1_000_000 * out_rate)
        
        self.total_usd += call_cost
        self.total_input_tokens += in_tok
        self.total_output_tokens += out_tok
        self.calls += 1
        self.model_calls[rate_key] = self.model_calls.get(rate_key, 0) + 1
        
        if self.total_usd > self.budget:
            raise BudgetExceeded(f"Budget exceeded! Cost: ${self.total_usd:.4f} > Cap: ${self.budget:.4f}")

    def report(self) -> dict:
        """Return the current accounting report."""
        return {
            "cost_usd": self.total_usd,
            "calls": self.calls,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "model_calls": dict(self.model_calls),
        }

METER = CostMeter()
