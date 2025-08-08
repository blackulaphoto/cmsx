"""
Base Scraper Classes - Common functionality for all scrapers
"""

import logging
import time
import requests
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import random

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_pages = config.get('max_pages', 2)
        self.rate_limit = config.get('rate_limit', 1)
        self.timeout = config.get('timeout', 30)
        self.search_url = config.get('search_url', '')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def _rate_limit_delay(self):
        """Rate limiting delay"""
        time.sleep(self.rate_limit + random.uniform(0, 1))
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[requests.Response]:
        """Make HTTP request with error handling"""
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
    
    @abstractmethod
    def scrape(self, keywords: str, location: str, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """Main scraping method - must be implemented by subclasses"""
        pass

class HTMLScraper(BaseScraper):
    """Base class for HTML-based scrapers"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
    
    def _parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content"""
        return BeautifulSoup(html, 'html.parser')
    
    def _extract_text(self, element) -> str:
        """Extract text from HTML element"""
        if element:
            return element.get_text(strip=True)
        return ""
    
    def _extract_href(self, element) -> str:
        """Extract href from HTML element"""
        if element and element.get('href'):
            return element.get('href')
        return ""
    
    def _clean_url(self, url: str, base_url: str) -> str:
        """Clean and normalize URL"""
        if not url:
            return ""
        if url.startswith('http'):
            return url
        return urljoin(base_url, url)

class BrowserScraper(BaseScraper):
    """Base class for browser-based scrapers (placeholder for future use)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Browser automation setup would go here
        # For now, this is a placeholder
    
    def scrape(self, keywords: str, location: str, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """Placeholder implementation"""
        logger.warning("BrowserScraper not implemented - using fallback")
        return [] 