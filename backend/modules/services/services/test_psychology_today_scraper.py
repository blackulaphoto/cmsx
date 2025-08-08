#!/usr/bin/env python3
"""
Simple test script for Psychology Today Scraper
"""

import requests
import logging
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import time
import random

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimplePsychologyTodayTester:
    """Simple tester for Psychology Today scraping functionality"""
    
    def __init__(self):
        self.base_url = "https://www.psychologytoday.com"
        self.search_url = "https://www.psychologytoday.com/us/therapists"
        self.session = requests.Session()
        
        # Set up headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def test_psychology_today_connection(self):
        """Test basic connection to Psychology Today"""
        try:
            logger.info("Testing Psychology Today connection...")
            response = self.session.get(self.base_url, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Psychology Today connection successful!")
                return True
            else:
                logger.error(f"❌ Psychology Today connection failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Psychology Today connection error: {e}")
            return False
    
    def test_search_page(self, location="Los Angeles, CA"):
        """Test the search page functionality"""
        try:
            logger.info(f"Testing Psychology Today search for: {location}")
            
            # Build search URL
            location_parts = location.split(',')
            if len(location_parts) >= 2:
                city = location_parts[0].strip()
                state = location_parts[1].strip()
                url_location = f"{city.lower().replace(' ', '-')}-{state.lower()}"
            else:
                url_location = location.lower().replace(' ', '-').replace(',', '')
            
            url = f"{self.search_url}/{url_location}"
            
            logger.info(f"Search URL: {url}")
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                logger.info("✅ Search page loaded successfully!")
                
                # Parse the page
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for therapist listings
                therapists = soup.find_all(['div', 'tr', 'li'], class_=lambda x: x and any(term in x.lower() for term in ['therapist', 'provider', 'listing', 'result']))
                
                if therapists:
                    logger.info(f"✅ Found {len(therapists)} potential therapist listings!")
                    return True
                else:
                    logger.warning("⚠️ No therapist listings found in expected format")
                    return False
                    
            else:
                logger.error(f"❌ Search page failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Search test error: {e}")
            return False
    
    def extract_sample_therapists(self, location="Los Angeles, CA"):
        """Extract sample therapists from Psychology Today"""
        try:
            logger.info(f"Extracting sample therapists for: {location}")
            
            # Build search URL
            location_parts = location.split(',')
            if len(location_parts) >= 2:
                city = location_parts[0].strip()
                state = location_parts[1].strip()
                url_location = f"{city.lower().replace(' ', '-')}-{state.lower()}"
            else:
                url_location = location.lower().replace(' ', '-').replace(',', '')
            
            url = f"{self.search_url}/{url_location}"
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for therapist information
                therapists = []
                
                # Try different selectors that might contain therapist info
                selectors = [
                    'div[class*="therapist"]',
                    'div[class*="provider"]', 
                    'div[class*="listing"]',
                    'div[class*="result"]',
                    'tr[class*="therapist"]',
                    'li[class*="therapist"]'
                ]
                
                for selector in selectors:
                    elements = soup.select(selector)
                    if elements:
                        logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        for element in elements[:3]:  # Just get first 3
                            therapist_info = self.extract_therapist_info(element)
                            if therapist_info:
                                therapists.append(therapist_info)
                        break
                
                if therapists:
                    logger.info(f"✅ Successfully extracted {len(therapists)} therapists!")
                    for i, therapist in enumerate(therapists, 1):
                        logger.info(f"Therapist {i}: {therapist}")
                    return therapists
                else:
                    logger.warning("⚠️ No therapists extracted")
                    return []
                    
            else:
                logger.error(f"❌ Failed to get search results: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Extraction error: {e}")
            return []
    
    def extract_therapist_info(self, element):
        """Extract therapist information from an element"""
        try:
            # Look for common therapist information patterns
            therapist_info = {}
            
            # Try to find name
            name_selectors = ['h1', 'h2', 'h3', 'h4', '.name', '.title', '.therapist-name']
            for selector in name_selectors:
                name_elem = element.select_one(selector)
                if name_elem:
                    therapist_info['name'] = name_elem.get_text(strip=True)
                    break
            
            # Try to find address
            address_selectors = ['.address', '.location', '[class*="address"]', '[class*="location"]']
            for selector in address_selectors:
                addr_elem = element.select_one(selector)
                if addr_elem:
                    therapist_info['address'] = addr_elem.get_text(strip=True)
                    break
            
            # Try to find phone
            phone_selectors = ['.phone', '.contact', '[class*="phone"]', '[class*="contact"]']
            for selector in phone_selectors:
                phone_elem = element.select_one(selector)
                if phone_elem:
                    therapist_info['phone'] = phone_elem.get_text(strip=True)
                    break
            
            # If we found at least a name, return the info
            if therapist_info.get('name'):
                return therapist_info
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error extracting therapist info: {e}")
            return None

def main():
    """Main test function"""
    logger.info("🧪 Starting Psychology Today Scraper Test")
    
    tester = SimplePsychologyTodayTester()
    
    # Test 1: Basic connection
    if not tester.test_psychology_today_connection():
        logger.error("❌ Basic connection test failed")
        return
    
    # Test 2: Search page
    if not tester.test_search_page():
        logger.error("❌ Search page test failed")
        return
    
    # Test 3: Extract therapists
    therapists = tester.extract_sample_therapists()
    
    if therapists:
        logger.info("🎉 Psychology Today scraper test successful!")
        logger.info(f"Found {len(therapists)} sample therapists")
    else:
        logger.warning("⚠️ Psychology Today scraper test completed but no therapists extracted")

if __name__ == "__main__":
    main() 