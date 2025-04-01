"""
Command-line interface for the PubMed Paper Fetcher.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from .fetcher import PubMedFetcher, Paper

app = typer.Typer(help="Fetch research papers from PubMed with pharmaceutical/biotech affiliations")
console = Console()


def save_to_csv(papers: list[Paper], output_file: str) -> None:
    """Save papers to a CSV file."""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'PubmedID', 'Title', 'Publication Date', 
            'Non-academic Author(s)', 'Company Affiliation(s)', 
            'Corresponding Author Email'
        ])
        for paper in papers:
            writer.writerow([
                paper.pubmed_id,
                paper.title,
                paper.publication_date.strftime('%Y-%m-%d'),
                '; '.join(paper.non_academic_authors),
                '; '.join(paper.company_affiliations),
                paper.corresponding_author_email or ''
            ])


def display_papers(papers: list[Paper]):
    """Display papers in a formatted table."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("PubMed ID", style="dim")
    table.add_column("Title")
    table.add_column("Date")
    table.add_column("Authors")
    table.add_column("Affiliations")
    table.add_column("Email")

    for paper in papers:
        table.add_row(
            paper.pubmed_id,
            paper.title,
            paper.publication_date.strftime('%Y-%m-%d'),
            '; '.join(paper.non_academic_authors),
            '; '.join(paper.company_affiliations),
            paper.corresponding_author_email or ''
        )

    console.print(table)


def parse_date_range(date_range: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """Parse date range string in format YYYY-YYYY or YYYY-MM-DD:YYYY-MM-DD."""
    try:
        if '-' in date_range:
            start, end = date_range.split('-')
            if len(start.split('-')) == 1:  # YYYY-YYYY format
                return datetime(int(start), 1, 1), datetime(int(end), 12, 31)
            else:  # YYYY-MM-DD:YYYY-MM-DD format
                return datetime.strptime(start, '%Y-%m-%d'), datetime.strptime(end, '%Y-%m-%d')
        return None, None
    except ValueError:
        console.print("[red]Invalid date range format. Use YYYY-YYYY or YYYY-MM-DD:YYYY-MM-DD[/red]")
        raise typer.Exit(1)


def load_progress(output_file: str) -> set[str]:
    """Load already processed PMIDs from output file."""
    processed_pmids = set()
    if Path(output_file).exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed_pmids.add(row['PubmedID'])
    return processed_pmids


@app.command()
def get_papers_list(
    query: str = typer.Argument(..., help="PubMed search query"),
    output_file: Optional[str] = typer.Option(None, "-f", "--file", help="Output CSV file path"),
    debug: bool = typer.Option(False, "-d", "--debug", help="Enable debug mode"),
    max_results: int = typer.Option(100, "-m", "--max-results", help="Maximum number of results to return"),
    date_range: Optional[str] = typer.Option(None, "--date-range", help="Date range in YYYY-YYYY or YYYY-MM-DD:YYYY-MM-DD format"),
    resume: bool = typer.Option(False, "-r", "--resume", help="Resume from previous run if output file exists")
):
    """Fetch papers from PubMed with pharmaceutical/biotech company affiliations."""
    try:
        # Parse date range if provided
        start_date, end_date = parse_date_range(date_range) if date_range else (None, None)

        # Initialize fetcher
        fetcher = PubMedFetcher(debug=debug)

        # Load progress if resuming
        processed_pmids = load_progress(output_file) if resume and output_file else set()

        # Create progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Fetching papers...", total=max_results)

            # Fetch papers
            papers = []
            for paper in fetcher.fetch_papers(query, max_results=max_results):
                if paper.pubmed_id not in processed_pmids:
                    if start_date and end_date:
                        if start_date <= paper.publication_date <= end_date:
                            papers.append(paper)
                    else:
                        papers.append(paper)
                    progress.update(task, advance=1)

                    # Save progress if output file specified
                    if output_file:
                        save_to_csv(papers, output_file)

        # Display results
        if papers:
            if not output_file:
                display_papers(papers)
            console.print(f"\n[green]Successfully fetched {len(papers)} papers[/green]")
        else:
            console.print("[yellow]No papers found matching the criteria[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app() 