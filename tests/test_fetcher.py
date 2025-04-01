"""
Tests for the PubMed Paper Fetcher.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from pubmed_paper_fetcher.fetcher import PubMedFetcher, Paper, Author


@pytest.fixture
def mock_response():
    """Create a mock response for testing."""
    mock = MagicMock()
    mock.json.return_value = {
        "esearchresult": {
            "idlist": ["12345678"]
        }
    }
    return mock


@pytest.fixture
def mock_paper_data():
    """Create mock paper data for testing."""
    return {
        "uid": "12345678",
        "title": "Test Paper",
        "pubdate": "2023-01-01",
        "authors": [
            {
                "name": "John Doe",
                "affiliations": ["Pharmaceutical Company Inc."],
                "email": "john@example.com",
                "is_corresponding": True
            }
        ]
    }


def test_fetch_papers(mock_response, mock_paper_data):
    """Test fetching papers from PubMed."""
    with patch("requests.get") as mock_get:
        # Mock the search response
        mock_get.return_value = mock_response
        
        # Mock the paper details response
        mock_paper_response = MagicMock()
        mock_paper_response.json.return_value = mock_paper_data
        mock_get.side_effect = [mock_response, mock_paper_response]
        
        fetcher = PubMedFetcher(debug=True)
        papers = fetcher.fetch_papers("test query")
        
        assert len(papers) == 1
        paper = papers[0]
        
        assert isinstance(paper, Paper)
        assert paper.pubmed_id == "12345678"
        assert paper.title == "Test Paper"
        assert isinstance(paper.publication_date, datetime)
        assert len(paper.authors) == 1
        assert paper.corresponding_author_email == "john@example.com"
        assert "Pharmaceutical Company Inc." in paper.company_affiliations


def test_extract_company_affiliations():
    """Test extracting company affiliations."""
    fetcher = PubMedFetcher()
    affiliations = [
        "University of Example",
        "Pharmaceutical Company Inc.",
        "Research Institute",
        "Biotech Solutions Ltd."
    ]
    
    company_affs = fetcher._extract_company_affiliations(affiliations)
    
    assert len(company_affs) == 2
    assert "Pharmaceutical Company Inc." in company_affs
    assert "Biotech Solutions Ltd." in company_affs
    assert "University of Example" not in company_affs


def test_process_paper_with_invalid_data():
    """Test processing paper with invalid data."""
    fetcher = PubMedFetcher()
    invalid_data = {
        "uid": "12345678",
        "title": "Test Paper",
        "pubdate": "invalid-date"
    }
    
    paper = fetcher._process_paper(invalid_data)
    assert paper is None 