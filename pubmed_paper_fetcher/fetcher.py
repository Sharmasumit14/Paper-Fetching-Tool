"""
Core module for fetching papers from PubMed with pharmaceutical/biotech affiliations.
"""

from datetime import datetime
from typing import List, Optional, Dict
import xml.etree.ElementTree as ET
import requests
from pydantic import BaseModel, Field
from dateutil.parser import parse
import time
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

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
    CACHE_DIR = Path.home() / ".pubmed_paper_fetcher" / "cache"
    CACHE_EXPIRY = 24 * 60 * 60  # 24 hours in seconds
    RATE_LIMIT_DELAY = 0.34  # seconds between requests (PubMed limit: 3 requests/second)
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.session = requests.Session()
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._last_request_time = 0
    
    def _rate_limit(self):
        """Ensure we don't exceed PubMed's rate limit"""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - time_since_last_request)
        self._last_request_time = time.time()
    
    def _get_cached_data(self, pmid: str) -> Optional[Dict]:
        """Get cached paper data if available and not expired"""
        cache_file = self.CACHE_DIR / f"{pmid}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                if time.time() - data['timestamp'] > self.CACHE_EXPIRY:
                    return None
                return data['paper']
        except Exception as e:
            logger.warning(f"Error reading cache for PMID {pmid}: {e}")
            return None
    
    def _cache_data(self, pmid: str, paper_data: Dict):
        """Cache paper data with timestamp"""
        try:
            cache_file = self.CACHE_DIR / f"{pmid}.json"
            with open(cache_file, 'w') as f:
                json.dump({
                    'timestamp': time.time(),
                    'paper': paper_data
                }, f)
        except Exception as e:
            logger.warning(f"Error caching data for PMID {pmid}: {e}")
    
    def _make_request(self, endpoint: str, params: Dict) -> requests.Response:
        """Make a request to PubMed API with retries and error handling"""
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                self._rate_limit()
                response = self.session.get(f"{self.BASE_URL}/{endpoint}", params=params)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(retry_delay * (attempt + 1))
    
    def _fetch_paper_details(self, pmid: str) -> Optional[Paper]:
        """Fetch detailed paper information from PubMed"""
        # Check cache first
        cached_data = self._get_cached_data(pmid)
        if cached_data:
            return Paper(**cached_data)

        try:
            params = {
                "db": "pubmed",
                "id": pmid,
                "retmode": "xml"
            }
            
            response = self._make_request("efetch.fcgi", params)
            root = ET.fromstring(response.content)
            
            # Extract article information
            article = root.find(".//PubmedArticle")
            if article is None:
                return None

            # Get title
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else "No title available"

            # Get publication date
            pub_date = article.find(".//PubDate")
            if pub_date is not None:
                year = pub_date.find("Year").text if pub_date.find("Year") is not None else "Unknown"
                month = pub_date.find("Month").text if pub_date.find("Month") is not None else "01"
                day = pub_date.find("Day").text if pub_date.find("Day") is not None else "01"
                publication_date = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
            else:
                publication_date = datetime.now()

            # Get authors and affiliations
            authors = []
            company_affiliations = []
            corresponding_author_email = None

            author_list = article.find(".//AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    last_name = author.find("LastName")
                    first_name = author.find("ForeName")
                    if last_name is not None and first_name is not None:
                        authors.append(f"{first_name.text} {last_name.text}")

                    # Check for corresponding author email
                    if author.find("AffiliationInfo") is not None:
                        for affil in author.findall(".//AffiliationInfo"):
                            affil_text = affil.find("Affiliation").text if affil.find("Affiliation") is not None else ""
                            if "@" in affil_text:
                                corresponding_author_email = affil_text
                                break

            # Extract company affiliations
            affiliations = article.findall(".//AffiliationInfo")
            for affil in affiliations:
                affil_text = affil.find("Affiliation").text if affil.find("Affiliation") is not None else ""
                if self._is_company_affiliation(affil_text):
                    company_affiliations.append(affil_text)

            paper = Paper(
                pubmed_id=pmid,
                title=title,
                publication_date=publication_date,
                authors=authors,
                non_academic_authors=authors,
                company_affiliations=company_affiliations,
                corresponding_author_email=corresponding_author_email
            )

            # Cache the paper data
            self._cache_data(pmid, paper.dict())

            return paper

        except Exception as e:
            logger.error(f"Error fetching details for PMID {pmid}: {e}")
            return None
    
    def _is_company_affiliation(self, affiliation: str) -> bool:
        """Check if the affiliation is from a pharmaceutical or biotech company"""
        company_keywords = [
            "pharmaceutical", "biotech", "biotechnology", "pharma", "drug company",
            "biopharmaceutical", "biopharma", "pharmaceuticals", "biopharmaceuticals",
            "pharmaceutical company", "biotech company", "biotechnology company",
            "drug development", "drug discovery", "clinical development",
            "research and development", "R&D", "research & development"
        ]
        
        affiliation_lower = affiliation.lower()
        return any(keyword in affiliation_lower for keyword in company_keywords)
    
    def _process_paper(self, pmid: str) -> Optional[Paper]:
        """Process a single paper and return if it has company affiliations"""
        if self.debug:
            logger.info(f"Fetching details for PMID: {pmid}")
        
        paper = self._fetch_paper_details(pmid)
        if paper and paper.company_affiliations:
            return paper
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
        if self.debug:
            logger.info(f"Searching PubMed for: {query}")

        try:
            # First, get the list of PMIDs
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": min(max_results, 1000)  # PubMed's maximum is 1000
            }
            
            response = self._make_request("esearch.fcgi", search_params)
            search_data = response.json()
            
            if "esearchresult" not in search_data or "idlist" not in search_data["esearchresult"]:
                logger.error("No results found or invalid response format")
                return []

            pmids = search_data["esearchresult"]["idlist"][:max_results]
            papers = []

            for pmid in pmids:
                paper = self._process_paper(pmid)
                if paper:
                    papers.append(paper)
                    if len(papers) >= max_results:
                        break

            return papers

        except Exception as e:
            logger.error(f"Error fetching papers: {e}")
            return [] 