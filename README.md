# PubMed Paper Fetcher

A Python tool to fetch research papers from PubMed with pharmaceutical/biotech company affiliations.

## Features

- Fetch papers using PubMed's full query syntax
- Identify papers with pharmaceutical/biotech company affiliations
- Export results to CSV or display in console
- Command-line interface with various options
- Type-safe implementation with comprehensive error handling

## Installation

This project uses Poetry for dependency management. To install:

1. Make sure you have Poetry installed:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Clone the repository:

```bash
git clone <repository-url>
cd pubmed-paper-fetcher
```

3. Install dependencies:

```bash
poetry install
```

## Usage

The tool can be used in two ways:

1. As a command-line tool:

```bash
poetry run get-papers-list "your search query" [options]
```

2. As a Python module:

```python
from pubmed_paper_fetcher.fetcher import PubMedFetcher

fetcher = PubMedFetcher(debug=True)
papers = fetcher.fetch_papers("your search query", max_results=50)
```

### Command-line Options

- `query`: PubMed search query (required)
- `-f, --file`: Output file path (CSV). If not provided, prints to console
- `-d, --debug`: Enable debug mode
- `-m, --max-results`: Maximum number of results to return (default: 100, max: 1000)

### PubMed Search Query Syntax

The tool supports PubMed's full query syntax. Here are some examples:

1. Basic search:

```bash
poetry run get-papers-list "cancer immunotherapy"
```

2. Search with field tags:

```bash
poetry run get-papers-list "cancer immunotherapy [title] AND (pharmaceutical OR biotech) [affiliation]"
```

3. Search with date range:

```bash
poetry run get-papers-list "cancer immunotherapy AND 2023:2025[Date - Publication]"
```

4. Search with multiple conditions:

```bash
poetry run get-papers-list "(cancer immunotherapy) AND (clinical trial[Publication Type]) AND (pharmaceutical OR biotech) [affiliation]"
```

### Output Format

The tool provides output in two formats:

1. Console Output:

```
Paper Details:
PubMed ID: 40164241
Title: Notch signaling and cancer: Insights into chemoresistance, immune evasion, and immunotherapy.
Publication Date: 2025-03-29
Non-academic Authors: Saadh Mohamed J, Adil Mohaned, Jawad Mahmood Jasem, Al-Nuaimi Ali M A
Company Affiliations: Faculty of Pharmacy, College of Pharmacy, Department of Pharmacy
Corresponding Author Email: example@email.com
--------------------------------------------------------------------------------
```

2. CSV Output (when using -f option):

```csv
PubmedID,Title,Publication Date,Non-academic Author(s),Company Affiliation(s),Corresponding Author Email
40164241,"Notch signaling and cancer: Insights into chemoresistance, immune evasion, and immunotherapy.",2025-03-29,"Saadh Mohamed J, Adil Mohaned, Jawad Mahmood Jasem, Al-Nuaimi Ali M A","Faculty of Pharmacy, College of Pharmacy, Department of Pharmacy",example@email.com
```

### Examples

1. Basic search with console output:

```bash
poetry run get-papers-list "cancer immunotherapy"
```

2. Save results to CSV:

```bash
poetry run get-papers-list "cancer immunotherapy" -f results.csv
```

3. Enable debug mode and limit results:

```bash
poetry run get-papers-list "cancer immunotherapy" -d -m 50
```

4. Search for papers with specific company affiliations:

```bash
poetry run get-papers-list "cancer immunotherapy AND (pharmaceutical OR biotech) [affiliation]" -f results.csv
```

## Project Structure

```
pubmed-paper-fetcher/
├── pubmed_paper_fetcher/
│   ├── __init__.py
│   ├── fetcher.py      # Core functionality
│   └── cli.py          # Command-line interface
├── pyproject.toml      # Project configuration and dependencies
└── README.md          # This file
```

## Development

### Setup Development Environment

1. Install development dependencies:

```bash
poetry install --with dev
```

2. Run tests:

```bash
poetry run pytest
```

3. Format code:

```bash
poetry run black .
poetry run isort .
```

4. Type checking:

```bash
poetry run mypy .
```

## Dependencies

- Python 3.8+
- requests: For HTTP requests to PubMed API
- pydantic: For data validation and serialization
- typer: For command-line interface
- rich: For beautiful console output
- python-dateutil: For date parsing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
