#!/usr/bin/env python3
"""
Simple test script for SAMHSA Treatment Scraper
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

class SimpleSAMHSATester:
    """Simple tester for SAMHSA scraping functionality"""
    
    def __init__(self):
        self.base_url = "https://findtreatment.samhsa.gov"
        self.search_url = "https://findtreatment.samhsa.gov/locator"
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
    
    def test_samhsa_connection(self):
        """Test basic connection to SAMHSA"""
        try:
            logger.info("Testing SAMHSA connection...")
            response = self.session.get(self.base_url, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ SAMHSA connection successful!")
                return True
            else:
                logger.error(f"❌ SAMHSA connection failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ SAMHSA connection error: {e}")
            return False
    
    def test_search_page(self, location="Los Angeles, CA"):
        """Test the search page functionality"""
        try:
            logger.info(f"Testing SAMHSA search for: {location}")
            
            # Build search URL
            params = {
                'location': location,
                'distance': 25
            }
            
            url = f"{self.search_url}?"
            url_params = []
            for key, value in params.items():
                url_params.append(f"{key}={quote_plus(str(value))}")
            url += "&".join(url_params)
            
            logger.info(f"Search URL: {url}")
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                logger.info("✅ Search page loaded successfully!")
                
                # Parse the page
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for treatment facility listings
                facilities = soup.find_all(['div', 'tr', 'li'], class_=lambda x: x and any(term in x.lower() for term in ['facility', 'treatment', 'center', 'clinic']))
                
                if facilities:
                    logger.info(f"✅ Found {len(facilities)} potential facility listings!")
                    return True
                else:
                    logger.warning("⚠️ No facility listings found in expected format")
                    return False
                    
            else:
                logger.error(f"❌ Search page failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Search test error: {e}")
            return False
    
    def extract_sample_facilities(self, location="Los Angeles, CA"):
        """Extract sample facilities from SAMHSA"""
        try:
            logger.info(f"Extracting sample facilities for: {location}")
            
            # Build search URL
            params = {
                'location': location,
                'distance': 25
            }
            
            url = f"{self.search_url}?"
            url_params = []
            for key, value in params.items():
                url_params.append(f"{key}={quote_plus(str(value))}")
            url += "&".join(url_params)
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for facility information
                facilities = []
                
                # Try different selectors that might contain facility info
                selectors = [
                    'div[class*="facility"]',
                    'div[class*="treatment"]', 
                    'div[class*="center"]',
                    'tr[class*="facility"]',
                    'li[class*="facility"]'
                ]
                
                for selector in selectors:
                    elements = soup.select(selector)
                    if elements:
                        logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        for element in elements[:3]:  # Just get first 3
                            facility_info = self.extract_facility_info(element)
                            if facility_info:
                                facilities.append(facility_info)
                        break
                
                if facilities:
                    logger.info(f"✅ Successfully extracted {len(facilities)} facilities!")
                    for i, facility in enumerate(facilities, 1):
                        logger.info(f"Facility {i}: {facility}")
                    return facilities
                else:
                    logger.warning("⚠️ No facilities extracted")
                    return []
                    
            else:
                logger.error(f"❌ Failed to get search results: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Extraction error: {e}")
            return []
    
    def extract_facility_info(self, element):
        """Extract facility information from an element"""
        try:
            # Look for common facility information patterns
            facility_info = {}
            
            # Try to find name
            name_selectors = ['h1', 'h2', 'h3', 'h4', '.name', '.title', '.facility-name']
            for selector in name_selectors:
                name_elem = element.select_one(selector)
                if name_elem:
                    facility_info['name'] = name_elem.get_text(strip=True)
                    break
            
            # Try to find address
            address_selectors = ['.address', '.location', '[class*="address"]', '[class*="location"]']
            for selector in address_selectors:
                addr_elem = element.select_one(selector)
                if addr_elem:
                    facility_info['address'] = addr_elem.get_text(strip=True)
                    break
            
            # Try to find phone
            phone_selectors = ['.phone', '.contact', '[class*="phone"]', '[class*="contact"]']
            for selector in phone_selectors:
                phone_elem = element.select_one(selector)
                if phone_elem:
                    facility_info['phone'] = phone_elem.get_text(strip=True)
                    break
            
            # If we found at least a name, return the info
            if facility_info.get('name'):
                return facility_info
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error extracting facility info: {e}")
            return None

def main():
    """Main test function"""
    logger.info("🧪 Starting SAMHSA Scraper Test")
    
    tester = SimpleSAMHSATester()
    
    # Test 1: Basic connection
    if not tester.test_samhsa_connection():
        logger.error("❌ Basic connection test failed")
        return
    
    # Test 2: Search page
    if not tester.test_search_page():
        logger.error("❌ Search page test failed")
        return
    
    # Test 3: Extract facilities
    facilities = tester.extract_sample_facilities()
    
    if facilities:
        logger.info("🎉 SAMHSA scraper test successful!")
        logger.info(f"Found {len(facilities)} sample facilities")
    else:
        logger.warning("⚠️ SAMHSA scraper test completed but no facilities extracted")

if __name__ == "__main__":
    main() 