"""Natural-language query in, product links out."""
import asyncio

import typer
from rich.console import Console
from rich.table import Table

from shopping_agent.pipeline import run

console = Console()


def main(
    query: str = typer.Argument(None, help="What you want, in plain English"),
    show: bool = typer.Option(False, "--show", help="Show the browser window (off by default)"),
    details: bool = typer.Option(False, "--details", help="Show detailed rich table output"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress the cost report line"),
    budget: float = typer.Option(0.10, "--budget", help="Maximum USD budget for Gemini calls"),
):
    if not query:
        query = console.input("[bold cyan]What are you looking for?[/] ")

    with console.status("[cyan]Searching...[/]"):     # spinner while it works, then nothing else
        results, cost_report = asyncio.run(run(query, headless=not show, verbose=False, budget=budget))

    if not results:
        console.print("[yellow]No matches found.[/] Try --show, or loosen the price/colour.")
    else:
        if details:
            table = Table(title="Best matches", show_lines=True)
            table.add_column("Price", style="green", no_wrap=True)
            table.add_column("Colour")
            table.add_column("Product")
            table.add_column("Link", style="blue")

            for r in results:
                p = r.product
                price = f"{p.currency or ''}{p.price}" if p.price is not None else "?"
                title = f"[link={p.url}]{p.title[:50]}[/link]"      # clickable in most terminals
                table.add_row(price, p.color or "?", title, p.url)

            console.print(table)
        else:
            for r in results:
                console.print(r.product.url)                  # just the links
                
    if not quiet:
        # e.g. "cost $0.013 · 11 calls · flash-lite×10 flash×1 · 2840 in / 210 out"
        models_str = " ".join(f"{k}×{v}" for k, v in cost_report["model_calls"].items())
        cost_line = (f"cost ${cost_report['cost_usd']:.3f} · {cost_report['calls']} calls · "
                     f"{models_str} · {cost_report['input_tokens']} in / {cost_report['output_tokens']} out")
        console.print(f"[dim]{cost_line}[/dim]")


if __name__ == "__main__":
    typer.run(main)
