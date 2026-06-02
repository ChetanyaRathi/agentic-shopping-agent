# Shopping Agent

A natural-language shopping assistant running directly from your terminal. Describe what you're looking for (e.g. "laptop bag, light blue, under $20"), and it discovers matching products, browses them using headless Playwright, extracts structured data using Gemini LLMs, and returns the top canonical links.

## Architecture
**Query → Plan → Discover → Browse → Extract → Filter → Rank → Links**

1. **Plan**: Parses the natural-language query into constraints using Gemini.
2. **Discover**: Uses Gemini Google Search Grounding to find candidate product URLs.
3. **Browse**: Visits candidate URLs via `@playwright/mcp` Server (running locally as a child process).
4. **Extract**: Extracts standard `Product` schemas from the accessibility snapshot. If a listing page is found, it automatically crawls into the child products.
5. **Filter & Rank**: Filters out items missing the price, stock, or completely wrong product type. Ranks by price and keyword/color match.
6. **Vision Fallback**: Validates colors via visual verification on product screenshots using Gemini Vision.

## Setup

Ensure you have Python 3.11+ and Node.js installed.

1. **Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install "mcp[cli]" google-genai pydantic typer rich python-dotenv
   ```
2. **Environment Variables**: Add your API key to a `.env` file in the root folder.
   ```bash
   GEMINI_API_KEY=your-api-key-here
   ```

## Usage

Run the agent via the CLI. It outputs plain canonical links by default.

```bash
python -m shopping_agent.cli "laptop bag, light blue, under $20"
```

To output a formatted rich table instead:
```bash
python -m shopping_agent.cli "laptop bag, light blue, under $20" --details
```

To see the browser while it runs (helps avoid some anti-bot detection):
```bash
python -m shopping_agent.cli "backpack under $30" --show
```

### Cost-Aware Design

Large language models can get expensive when chained in a pipeline. The Shopping Agent features a dedicated cost accounting layer to track expenses per-run:

- **Model Routing**: It defaults to the ultra-cheap `gemini-2.5-flash-lite`, only escalating to `gemini-2.5-flash` if parsing fails or grounding search is required.
- **Budget Cap**: It strictly enforces a runtime budget (default $0.10). If the cost exceeds this cap, it stops crawling and gracefully returns the partial results found so far.
- **Cost Report**: At the end of every run, it prints a single summary line so you know exactly what you spent:

```bash
cost $0.003 · 12 calls · gemini-2.5-flash-lite×10 gemini-2.5-flash×2 · 18500 in / 1200 out
```
