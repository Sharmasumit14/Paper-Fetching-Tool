"""
Core module for fetching papers from PubMed with pharmaceutical/biotech affiliations.
"""

from datetime import datetime
from typing import List, Optional
import xml.etree.ElementTree as ET
import requests
from pydantic import BaseModel, Field
from dateutil.parser import parse


class Author(BaseModel):
    """Represents an author with their affiliations."""
    name: str
    affiliations: List[str] = Field(default_factory=list)
    email: Optional[str] = None
    is_corresponding: bool = False


class Paper(BaseModel):
    """Represents a research paper with its metadata."""
    pubmed_id: str
    title: str
    publication_date: datetime
    authors: List[Author]
    non_academic_authors: List[str] = Field(default_factory=list)
    company_affiliations: List[str] = Field(default_factory=list)
    corresponding_author_email: Optional[str] = None


class PubMedFetcher:
    """Handles fetching and processing papers from PubMed."""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def _log(self, message: str) -> None:
        """Log debug messages if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}")
    
    def _fetch_paper_details(self, pmid: str) -> dict:
        """Fetch detailed information for a specific paper."""
        url = f"{self.BASE_URL}/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml"
        }
        
        self._log(f"Fetching details for PMID: {pmid}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.content)
        article = root.find(".//Article")
        if article is None:
            return {}
        
        # Extract basic information
        title = article.find(".//ArticleTitle")
        title = title.text if title is not None else ""
        
        # Extract publication date
        pub_date = article.find(".//PubDate")
        if pub_date is not None:
            year = pub_date.find("Year")
            month = pub_date.find("Month")
            day = pub_date.find("Day")
            pub_date_str = f"{year.text if year is not None else '2025'}-{month.text if month is not None else '01'}-{day.text if day is not None else '01'}"
        else:
            pub_date_str = "2025-01-01"
        
        # Extract authors and affiliations
        authors = []
        for author_elem in article.findall(".//Author"):
            name_parts = []
            last_name = author_elem.find("LastName")
            fore_name = author_elem.find("ForeName")
            if last_name is not None:
                name_parts.append(last_name.text)
            if fore_name is not None:
                name_parts.append(fore_name.text)
            
            name = " ".join(name_parts) if name_parts else ""
            
            # Get affiliations
            affiliations = []
            for aff in author_elem.findall(".//Affiliation"):
                if aff.text:
                    affiliations.append(aff.text)
            
            # Check if author is corresponding
            is_corresponding = False
            email = None
            for aff in affiliations:
                if "@" in aff:
                    email = aff.split("@")[0] + "@" + aff.split("@")[1].split()[0]
                    is_corresponding = True
            
            authors.append({
                "name": name,
                "affiliations": affiliations,
                "email": email,
                "is_corresponding": is_corresponding
            })
        
        return {
            "uid": pmid,
            "title": title,
            "pubdate": pub_date_str,
            "authors": authors
        }
    
    def _extract_company_affiliations(self, affiliations: List[str]) -> List[str]:
        """Extract pharmaceutical/biotech company affiliations."""
        company_keywords = [
            "pharmaceutical", "biotech", "biotechnology", "pharma",
            "therapeutics", "biosciences", "laboratories", "inc.", "corp.",
            "corporation", "ltd.", "limited", "llc", "gmbh"
        ]
        company_affs = []
        for aff in affiliations:
            if any(keyword.lower() in aff.lower() for keyword in company_keywords):
                # Clean up the affiliation string
                clean_aff = aff.split(",")[0].strip()  # Take first part before comma
                if clean_aff:
                    company_affs.append(clean_aff)
        return company_affs
    
    def _process_paper(self, paper_data: dict) -> Optional[Paper]:
        """Process raw paper data into a Paper object."""
        try:
            # Extract basic information
            uid = paper_data.get("uid", "")
            title = paper_data.get("title", "")
            pub_date = parse(paper_data.get("pubdate", ""))
            
            # Process authors and affiliations
            authors = []
            non_academic_authors = []
            company_affiliations = []
            corresponding_email = None
            
            # Extract author information from the paper data
            author_list = paper_data.get("authors", [])
            
            for author_data in author_list:
                author = Author(
                    name=author_data.get("name", ""),
                    affiliations=author_data.get("affiliations", []),
                    email=author_data.get("email"),
                    is_corresponding=author_data.get("is_corresponding", False)
                )
                authors.append(author)
                
                if author.is_corresponding:
                    corresponding_email = author.email
                
                # Check for non-academic affiliations
                company_affs = self._extract_company_affiliations(author.affiliations)
                if company_affs:
                    non_academic_authors.append(author.name)
                    company_affiliations.extend(company_affs)
            
            # Only return papers that have at least one company affiliation
            if not company_affiliations:
                return None
            
            return Paper(
                pubmed_id=uid,
                title=title,
                publication_date=pub_date,
                authors=authors,
                non_academic_authors=non_academic_authors,
                company_affiliations=list(set(company_affiliations)),
                corresponding_author_email=corresponding_email
            )
        except Exception as e:
            self._log(f"Error processing paper: {str(e)}")
            return None
    
    def fetch_papers(self, query: str, max_results: int = 100) -> List[Paper]:
        """
        Fetch papers from PubMed based on the query.
        
        Args:
            query: PubMed search query
            max_results: Maximum number of results to return
            
        Returns:
            List of Paper objects
        """
        # First, search for papers
        search_url = f"{self.BASE_URL}/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max_results
        }
        
        self._log(f"Searching PubMed with query: {query}")
        response = requests.get(search_url, params=search_params)
        response.raise_for_status()
        
        search_results = response.json()
        pmids = search_results.get("esearchresult", {}).get("idlist", [])
        
        # Fetch details for each paper
        papers = []
        for pmid in pmids:
            try:
                paper_data = self._fetch_paper_details(pmid)
                paper = self._process_paper(paper_data)
                if paper:
                    papers.append(paper)
            except Exception as e:
                self._log(f"Error fetching paper {pmid}: {str(e)}")
                continue
        
        return papers 