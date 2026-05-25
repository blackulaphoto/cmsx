#!/usr/bin/env python3
"""
Simple Job Search Tools - What case managers actually do
Generate search URLs for clients instead of scraping thousands of listings
"""

from typing import Dict, List, Optional
from urllib.parse import urlencode, quote_plus
import logging

logger = logging.getLogger(__name__)


class JobSearchURLGenerator:
    """Generate job search URLs that case managers can send to clients"""

    @staticmethod
    def generate_craigslist_url(keywords: str, location: str = "losangeles") -> str:
        """Generate Craigslist job search URL"""
        # Map common locations to Craigslist subdomains
        location_map = {
            "los angeles": "losangeles",
            "la": "losangeles",
            "orange county": "orangecounty",
            "san diego": "sandiego",
            "inland empire": "inlandempire",
            "ventura": "ventura",
            "santa barbara": "santabarbara",
        }

        subdomain = location_map.get(location.lower(), "losangeles")
        query = quote_plus(keywords)

        return f"https://{subdomain}.craigslist.org/search/jjj?query={query}&sort=date"

    @staticmethod
    def generate_indeed_url(keywords: str, location: str = "Los Angeles, CA") -> str:
        """Generate Indeed job search URL"""
        params = {
            'q': keywords,
            'l': location,
            'sort': 'date',
            'fromage': '14',  # Last 14 days
        }
        return f"https://www.indeed.com/jobs?{urlencode(params)}"

    @staticmethod
    def generate_ziprecruiter_url(keywords: str, location: str = "Los Angeles, CA") -> str:
        """Generate ZipRecruiter job search URL"""
        params = {
            'search': keywords,
            'location': location,
        }
        return f"https://www.ziprecruiter.com/jobs-search?{urlencode(params)}"

    @staticmethod
    def generate_linkedin_url(keywords: str, location: str = "Los Angeles, CA") -> str:
        """Generate LinkedIn job search URL"""
        params = {
            'keywords': keywords,
            'location': location,
            'f_TPR': 'r2592000',  # Past month
            'position': '1',
            'pageNum': '0',
        }
        return f"https://www.linkedin.com/jobs/search/?{urlencode(params)}"

    @staticmethod
    def generate_monster_url(keywords: str, location: str = "Los Angeles, CA") -> str:
        """Generate Monster job search URL"""
        params = {
            'q': keywords,
            'where': location,
        }
        return f"https://www.monster.com/jobs/search/?{urlencode(params)}"

    @staticmethod
    def generate_government_jobs_url(keywords: str = "") -> str:
        """Generate USAJobs (federal) or CalCareers (state) URL"""
        if keywords:
            params = {'keyword': keywords}
            return f"https://www.usajobs.gov/Search/Results?{urlencode(params)}"
        return "https://www.usajobs.gov/Search/Results"

    @staticmethod
    def generate_background_friendly_searches(keywords: str, location: str = "Los Angeles, CA") -> List[Dict[str, str]]:
        """
        Generate search URLs with background-friendly keywords added
        These searches add terms like 'second chance', 'fair chance', 'felon friendly'
        """
        background_terms = [
            f"{keywords} second chance employer",
            f"{keywords} fair chance hiring",
            f"{keywords} ban the box",
        ]

        searches = []
        for term in background_terms:
            searches.append({
                'platform': 'Indeed',
                'keywords': term,
                'url': JobSearchURLGenerator.generate_indeed_url(term, location)
            })
            searches.append({
                'platform': 'Craigslist',
                'keywords': term,
                'url': JobSearchURLGenerator.generate_craigslist_url(term, location.split(',')[0])
            })

        return searches

    @staticmethod
    def generate_all_search_urls(keywords: str, location: str = "Los Angeles, CA") -> Dict[str, str]:
        """Generate search URLs for all major job platforms"""
        loc_short = location.split(',')[0].strip()

        return {
            'craigslist': JobSearchURLGenerator.generate_craigslist_url(keywords, loc_short),
            'indeed': JobSearchURLGenerator.generate_indeed_url(keywords, location),
            'ziprecruiter': JobSearchURLGenerator.generate_ziprecruiter_url(keywords, location),
            'linkedin': JobSearchURLGenerator.generate_linkedin_url(keywords, location),
            'monster': JobSearchURLGenerator.generate_monster_url(keywords, location),
            'government': JobSearchURLGenerator.generate_government_jobs_url(keywords),
        }


class BackgroundFriendlyEmployerList:
    """Known background-friendly employers in LA area"""

    EMPLOYERS = [
        {
            'name': 'Goodwill Industries',
            'industry': 'Retail/Warehouse',
            'why': 'Explicitly hires people with records as part of their mission',
            'careers_url': 'https://www.goodwill.org/jobs/',
        },
        {
            'name': 'The Salvation Army',
            'industry': 'Retail/Social Services',
            'why': 'Second chance employer with various positions',
            'careers_url': 'https://www.salvationarmyusa.org/usn/employment/',
        },
        {
            'name': 'Homeboy Industries',
            'industry': 'Food Service/Manufacturing',
            'why': 'Dedicated to hiring formerly incarcerated individuals',
            'careers_url': 'https://homeboyindustries.org/jobs/',
        },
        {
            'name': 'Amazon Warehouses',
            'industry': 'Warehouse/Logistics',
            'why': 'Fair chance hiring practices, case-by-case review',
            'careers_url': 'https://hiring.amazon.com/',
        },
        {
            'name': 'Walmart',
            'industry': 'Retail',
            'why': 'Fair chance employer, hires people with records',
            'careers_url': 'https://careers.walmart.com/',
        },
        {
            'name': 'Greyston Bakery',
            'industry': 'Food Production',
            'why': 'Open hiring - no questions asked policy',
            'careers_url': 'https://greystonbakery.com/pages/careers',
        },
        {
            'name': 'Dave\'s Killer Bread',
            'industry': 'Food Production',
            'why': 'Founded by formerly incarcerated person, second chance employer',
            'careers_url': 'https://www.daveskillerbread.com/second-chance-employment',
        },
    ]

    @staticmethod
    def get_by_industry(industry: str = None) -> List[Dict[str, str]]:
        """Get background-friendly employers, optionally filtered by industry"""
        if not industry:
            return BackgroundFriendlyEmployerList.EMPLOYERS

        industry_lower = industry.lower()
        return [
            emp for emp in BackgroundFriendlyEmployerList.EMPLOYERS
            if industry_lower in emp['industry'].lower()
        ]


def get_job_search_resources(keywords: str, location: str = "Los Angeles, CA") -> Dict[str, any]:
    """
    What a case manager actually needs: search URLs + known good employers
    """
    generator = JobSearchURLGenerator()

    return {
        'success': True,
        'keywords': keywords,
        'location': location,
        'search_urls': generator.generate_all_search_urls(keywords, location),
        'background_friendly_searches': generator.generate_background_friendly_searches(keywords, location)[:6],
        'known_employers': BackgroundFriendlyEmployerList.get_by_industry(),
        'instructions': {
            'for_case_manager': 'Send these search URLs to your client via text or email',
            'for_client': 'Visit these job boards and apply directly. Check daily for new postings.',
            'tip': 'Craigslist and Indeed update most frequently - check these daily'
        }
    }
