"""
Command-line interface for the PubMed Paper Fetcher.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .fetcher import PubMedFetcher

app = typer.Typer(help="Fetch research papers from PubMed with pharmaceutical/biotech affiliations")
console = Console()


def save_to_csv(papers: list, output_file: Path) -> None:
    """Save papers to a CSV file."""
    fieldnames = [
        "PubmedID",
        "Title",
        "Publication Date",
        "Non-academic Author(s)",
        "Company Affiliation(s)",
        "Corresponding Author Email"
    ]
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for paper in papers:
            writer.writerow({
                "PubmedID": paper.pubmed_id,
                "Title": paper.title,
                "Publication Date": paper.publication_date.strftime("%Y-%m-%d"),
                "Non-academic Author(s)": "; ".join(paper.non_academic_authors),
                "Company Affiliation(s)": "; ".join(paper.company_affiliations),
                "Corresponding Author Email": paper.corresponding_author_email or ""
            })


@app.command()
def main(
    query: str = typer.Argument(..., help="PubMed search query"),
    output_file: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="Output file path (CSV). If not provided, prints to console",
        dir_okay=False,
        file_okay=True,
        writable=True,
        resolve_path=True,
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug mode",
    ),
    max_results: int = typer.Option(
        100,
        "--max-results",
        "-m",
        help="Maximum number of results to return",
        min=1,
        max=1000,
    ),
):
    """
    Fetch research papers from PubMed with pharmaceutical/biotech affiliations.
    """
    try:
        fetcher = PubMedFetcher(debug=debug)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching papers...", total=None)
            papers = fetcher.fetch_papers(query, max_results=max_results)
            progress.update(task, completed=True)
        
        if not papers:
            console.print("[yellow]No papers found matching the criteria.[/yellow]")
            raise typer.Exit(1)
        
        if output_file:
            save_to_csv(papers, output_file)
            console.print(f"[green]Results saved to {output_file}[/green]")
        else:
            # Print results to console in a formatted way
            for paper in papers:
                console.print("\n[bold blue]Paper Details:[/bold blue]")
                console.print(f"PubMed ID: {paper.pubmed_id}")
                console.print(f"Title: {paper.title}")
                console.print(f"Publication Date: {paper.publication_date.strftime('%Y-%m-%d')}")
                console.print(f"Non-academic Authors: {', '.join(paper.non_academic_authors)}")
                console.print(f"Company Affiliations: {', '.join(paper.company_affiliations)}")
                console.print(f"Corresponding Author Email: {paper.corresponding_author_email or 'N/A'}")
                console.print("-" * 80)
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app() 