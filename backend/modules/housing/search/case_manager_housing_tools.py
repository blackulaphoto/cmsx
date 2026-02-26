"""
Enhanced Housing Search for Case Managers
Transforms generic rental search into case management workflow tools
"""

import re
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode, urlparse
import asyncio

# Import the existing housing search coordinator
try:
    from backend.search.coordinator import get_coordinator
except ImportError:
    # Fallback import path
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'search'))
    from coordinator import get_coordinator

class CaseManagerHousingTools:
    """Enhanced housing search tools specifically designed for case manager workflows"""
    
    def __init__(self):
        self.coordinator = get_coordinator()
        self.client_profiles = {}
        self.saved_resources = {}
        self.housing_tracker = {
            "pending_applications": [],
            "scheduled_viewings": [],
            "housing_placed": [],
            "follow_up_needed": []
        }
    
    async def enhanced_case_manager_search(self, query: str, location: str, 
                                         client_id: str = None, client_budget: int = None, 
                                         client_needs: List[str] = None) -> Dict[str, Any]:
        """Case manager specific search with workflow optimization"""
        
        # Get client profile if available
        client_profile = self.get_client_profile(client_id) if client_id else {}
        
        # Use client data if not provided in parameters
        if not client_budget and client_profile.get('budget'):
            client_budget = client_profile['budget']
        if not client_needs and client_profile.get('needs'):
            client_needs = client_profile['needs']
        
        # Perform the housing search using existing coordinator
        try:
            search_results = await self.coordinator.search_housing(
                query=f"{query} {location}",
                location=location
            )
            
            if not search_results.get('success'):
                error_detail = search_results.get('error', 'Housing search failed')
                return self._create_error_response(error_detail)
            
            # Transform results for case manager workflow
            enhanced_results = []
            raw_results = search_results.get('results') or search_results.get('housing_listings') or []
            for result in raw_results:
                enhanced = await self._enhance_result_for_case_manager(
                    result, client_budget, client_needs, client_id
                )
                enhanced_results.append(enhanced)
            
            # Sort by case manager relevance
            enhanced_results = self._prioritize_for_case_managers(enhanced_results, client_budget, client_needs)
            
            # Create case manager dashboard response
            return self._create_case_manager_response(
                enhanced_results, client_id, client_budget, client_needs, query, location
            )
            
        except Exception as e:
            return self._create_error_response(f"Search error: {str(e)}")
    
    async def _enhance_result_for_case_manager(self, result: Dict, client_budget: int, 
                                             client_needs: List[str], client_id: str) -> Dict[str, Any]:
        """Transform a search result into case manager workflow format"""
        
        # Extract key information
        url = result.get('link', result.get('url', ''))
        title = result.get('title', '')
        description = result.get('description', '')
        
        # Calculate client match score
        match_score = self._calculate_client_match_score(result, client_budget, client_needs)
        
        # Generate quick actions
        quick_actions = self._generate_quick_actions(result, client_id)
        
        # Extract contact information
        contact_info = self._extract_contact_info(result)
        
        # Determine rental site
        site_info = self._identify_rental_site(url)
        
        # Extract pricing information
        pricing_info = self._extract_pricing_info(title, description)
        
        return {
            "id": f"cm_{hash(url)}",
            "title": title,
            "url": url,
            "description": description,
            "site_info": site_info,
            "pricing_info": pricing_info,
            "contact_info": contact_info,
            "match_score": match_score,
            "match_reasons": self._get_match_reasons(result, client_budget, client_needs),
            "quick_actions": quick_actions,
            "case_manager_notes": "",
            "follow_up_date": None,
            "client_saved": False,
            "priority_level": self._determine_priority_level(match_score, site_info)
        }
    
    def _calculate_client_match_score(self, result: Dict, budget: int, needs: List[str]) -> int:
        """Calculate how well this result matches client needs (0-100)"""
        score = 0
        max_score = 100
        
        title = result.get('title', '').lower()
        description = result.get('description', '').lower()
        text = f"{title} {description}"
        
        # Budget matching (40 points max)
        if budget:
            extracted_prices = self._extract_prices_from_text(text)
            if extracted_prices:
                min_price = min(extracted_prices)
                if min_price <= budget:
                    score += 40
                elif min_price <= budget * 1.1:  # Within 10% of budget
                    score += 25
                elif min_price <= budget * 1.2:  # Within 20% of budget
                    score += 10
        
        # Needs matching (60 points max, distributed among needs)
        if needs:
            points_per_need = 60 // len(needs)
            
            for need in needs:
                if need.lower() in ['pet_friendly', 'pets_allowed']:
                    if any(word in text for word in ['pet', 'dog', 'cat', 'animal']):
                        score += points_per_need
                
                elif need.lower() in ['near_transit', 'public_transport']:
                    if any(word in text for word in ['metro', 'bus', 'transit', 'subway', 'train']):
                        score += points_per_need
                
                elif need.lower() in ['wheelchair_accessible', 'accessible']:
                    if any(word in text for word in ['accessible', 'wheelchair', 'ada', 'disabled']):
                        score += points_per_need
                
                elif need.lower() in ['parking', 'garage']:
                    if any(word in text for word in ['parking', 'garage', 'space']):
                        score += points_per_need
                
                elif need.lower() in ['laundry', 'washer_dryer']:
                    if any(word in text for word in ['laundry', 'washer', 'dryer']):
                        score += points_per_need
        
        return min(score, max_score)
    
    def _get_match_reasons(self, result: Dict, budget: int, needs: List[str]) -> List[str]:
        """Get human-readable reasons why this result matches the client"""
        reasons = []
        
        title = result.get('title', '').lower()
        description = result.get('description', '').lower()
        text = f"{title} {description}"
        
        # Budget reasons
        if budget:
            extracted_prices = self._extract_prices_from_text(text)
            if extracted_prices:
                min_price = min(extracted_prices)
                if min_price <= budget:
                    reasons.append(f"✅ Under budget (${min_price:,} ≤ ${budget:,})")
                elif min_price <= budget * 1.1:
                    reasons.append(f"⚠️ Slightly over budget (${min_price:,})")
        
        # Needs reasons
        if needs:
            for need in needs:
                if need.lower() in ['pet_friendly', 'pets_allowed']:
                    if any(word in text for word in ['pet', 'dog', 'cat', 'animal']):
                        reasons.append("✅ Pet-friendly options found")
                
                elif need.lower() in ['near_transit', 'public_transport']:
                    if any(word in text for word in ['metro', 'bus', 'transit', 'subway', 'train']):
                        reasons.append("✅ Near public transportation")
                
                elif need.lower() in ['wheelchair_accessible', 'accessible']:
                    if any(word in text for word in ['accessible', 'wheelchair', 'ada']):
                        reasons.append("✅ Wheelchair accessible options")
        
        if not reasons:
            reasons.append("ℹ️ General housing resource")
        
        return reasons
    
    def _generate_quick_actions(self, result: Dict, client_id: str) -> List[Dict[str, str]]:
        """Generate quick action buttons for case managers"""
        actions = []
        url = result.get('link', result.get('url', ''))
        site_info = self._identify_rental_site(url)
        
        # Site-specific quick actions
        if site_info['name'] == 'Apartments.com':
            actions.append({
                "type": "quick_search",
                "label": "Quick Search Units",
                "action": "open_filtered_search",
                "url": f"{url}?available=true",
                "icon": "search"
            })
        
        elif site_info['name'] == 'Zillow':
            actions.append({
                "type": "quick_search", 
                "label": "View All Zillow Units",
                "action": "open_filtered_search",
                "url": url,
                "icon": "home"
            })
        
        elif site_info['name'] == 'Craigslist':
            actions.append({
                "type": "contact_scan",
                "label": "Scan for Contacts",
                "action": "extract_craigslist_contacts",
                "url": url,
                "icon": "phone"
            })
        
        # Universal actions
        actions.extend([
            {
                "type": "save_client",
                "label": "Save for Client",
                "action": "save_to_client_resources",
                "client_id": client_id,
                "icon": "bookmark"
            },
            {
                "type": "schedule_followup",
                "label": "Schedule Follow-up",
                "action": "create_followup_reminder",
                "client_id": client_id,
                "icon": "calendar"
            },
            {
                "type": "get_contacts",
                "label": "Extract Contacts",
                "action": "extract_contact_info",
                "url": url,
                "icon": "user"
            }
        ])
        
        return actions
    
    def _identify_rental_site(self, url: str) -> Dict[str, str]:
        """Identify which rental site this result is from"""
        if not url:
            return {"name": "Unknown", "color": "gray", "icon": "home"}
        
        url_lower = url.lower()
        
        if 'zillow.com' in url_lower:
            return {"name": "Zillow", "color": "blue", "icon": "home"}
        elif 'apartments.com' in url_lower:
            return {"name": "Apartments.com", "color": "red", "icon": "building"}
        elif 'craigslist.org' in url_lower:
            return {"name": "Craigslist", "color": "purple", "icon": "list"}
        elif 'rent.com' in url_lower:
            return {"name": "Rent.com", "color": "green", "icon": "key"}
        elif 'realtor.com' in url_lower:
            return {"name": "Realtor.com", "color": "orange", "icon": "home"}
        elif 'trulia.com' in url_lower:
            return {"name": "Trulia", "color": "teal", "icon": "map"}
        else:
            return {"name": "Rental Site", "color": "gray", "icon": "home"}
    
    def _extract_pricing_info(self, title: str, description: str) -> Dict[str, Any]:
        """Extract pricing information from title and description"""
        text = f"{title} {description}"
        prices = self._extract_prices_from_text(text)
        
        return {
            "prices_found": prices,
            "min_price": min(prices) if prices else None,
            "max_price": max(prices) if prices else None,
            "price_display": f"${min(prices):,}" if prices else "See listing for pricing"
        }
    
    def _extract_prices_from_text(self, text: str) -> List[int]:
        """Extract dollar amounts from text"""
        # Find all dollar amounts
        price_pattern = r'\$[\d,]+(?:\.\d{2})?'
        matches = re.findall(price_pattern, text)
        
        prices = []
        for match in matches:
            # Clean and convert to int
            clean_price = match.replace('$', '').replace(',', '').replace('.00', '')
            try:
                price = int(clean_price)
                # Filter reasonable rental prices (between $500 and $10,000)
                if 500 <= price <= 10000:
                    prices.append(price)
            except ValueError:
                continue
        
        return prices
    
    def _extract_contact_info(self, result: Dict) -> Dict[str, Any]:
        """Extract contact information from result"""
        text = f"{result.get('title', '')} {result.get('description', '')}"
        
        # Phone number patterns
        phone_pattern = r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
        phones = re.findall(phone_pattern, text)
        
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        return {
            "phones": phones[:3],  # Limit to first 3 found
            "emails": emails[:2],  # Limit to first 2 found
            "has_contact": len(phones) > 0 or len(emails) > 0
        }
    
    def _determine_priority_level(self, match_score: int, site_info: Dict) -> str:
        """Determine priority level for case manager attention"""
        if match_score >= 80:
            return "high"
        elif match_score >= 60:
            return "medium"
        elif site_info['name'] in ['Zillow', 'Apartments.com', 'Realtor.com']:
            return "medium"  # Trusted sites get medium priority even with lower scores
        else:
            return "low"
    
    def _prioritize_for_case_managers(self, results: List[Dict], budget: int, needs: List[str]) -> List[Dict]:
        """Sort results by case manager relevance"""
        def sort_key(result):
            # Primary sort: match score (descending)
            # Secondary sort: priority level (high > medium > low)
            # Tertiary sort: trusted sites first
            
            priority_weights = {"high": 3, "medium": 2, "low": 1}
            trusted_sites = ['Zillow', 'Apartments.com', 'Realtor.com', 'Rent.com']
            
            return (
                -result['match_score'],  # Negative for descending
                -priority_weights.get(result['priority_level'], 0),
                -1 if result['site_info']['name'] in trusted_sites else 0
            )
        
        return sorted(results, key=sort_key)
    
    def _create_case_manager_response(self, results: List[Dict], client_id: str, 
                                    budget: int, needs: List[str], query: str, location: str) -> Dict[str, Any]:
        """Create the case manager dashboard response"""
        
        # Get client info
        client_info = self.get_client_profile(client_id) if client_id else {}
        
        # Calculate summary stats
        high_priority = len([r for r in results if r['priority_level'] == 'high'])
        medium_priority = len([r for r in results if r['priority_level'] == 'medium'])
        with_contacts = len([r for r in results if r['contact_info']['has_contact']])
        
        return {
            "success": True,
            "case_manager_view": True,
            "search_info": {
                "query": query,
                "location": location,
                "client_id": client_id,
                "client_name": client_info.get('name', 'Unknown Client'),
                "budget": budget,
                "needs": needs or [],
                "search_timestamp": datetime.now().isoformat()
            },
            "summary": {
                "total_results": len(results),
                "high_priority": high_priority,
                "medium_priority": medium_priority,
                "low_priority": len(results) - high_priority - medium_priority,
                "with_contacts": with_contacts,
                "budget_matches": len([r for r in results if r['match_score'] >= 40])
            },
            "results": results,
            "quick_actions": self._get_dashboard_quick_actions(client_id, budget, location),
            "client_tracker": self._get_client_housing_tracker(client_id),
            "saved_resources": self._get_saved_resources(client_id)
        }
    
    def _get_dashboard_quick_actions(self, client_id: str, budget: int, location: str) -> List[Dict]:
        """Get quick actions for the case manager dashboard"""
        actions = []
        
        if budget:
            actions.append({
                "type": "budget_search",
                "label": f"Search Under ${budget:,}",
                "action": "search_by_budget",
                "params": {"budget": budget, "location": location}
            })
        
        actions.extend([
            {
                "type": "bulk_search",
                "label": "Search All Clients",
                "action": "bulk_client_search",
                "params": {"location": location}
            },
            {
                "type": "weekly_report",
                "label": "Weekly Housing Report",
                "action": "generate_housing_report",
                "params": {"client_id": client_id}
            },
            {
                "type": "emergency_housing",
                "label": "Emergency Housing",
                "action": "search_emergency_housing",
                "params": {"location": location}
            }
        ])
        
        return actions
    
    def _get_client_housing_tracker(self, client_id: str) -> Dict[str, Any]:
        """Get housing tracker for specific client"""
        if not client_id:
            return {"message": "No client selected"}
        
        # This would integrate with your client database
        return {
            "pending_applications": [
                {
                    "property": "Vista Apartments",
                    "applied_date": "2025-08-05",
                    "follow_up_date": "2025-08-12",
                    "status": "pending"
                }
            ],
            "scheduled_viewings": [
                {
                    "property": "Broadway Lofts",
                    "viewing_date": "2025-08-11",
                    "time": "2:00 PM",
                    "contact": "(555) 123-4567"
                }
            ],
            "saved_resources": 8,
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_saved_resources(self, client_id: str) -> List[Dict]:
        """Get saved housing resources for client"""
        return [
            {
                "name": "LA Housing Authority",
                "type": "waitlist",
                "url": "https://hacla.org",
                "notes": "Section 8 waitlist opens quarterly"
            },
            {
                "name": "Emergency Housing Contacts",
                "type": "emergency",
                "phone": "(211)",
                "notes": "24/7 emergency housing assistance"
            }
        ]
    
    def get_client_profile(self, client_id: str) -> Dict[str, Any]:
        """Get client profile information"""
        try:
            with sqlite3.connect("databases/core_clients.db") as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT first_name, last_name, housing_status
                    FROM clients
                    WHERE client_id = ?
                    """,
                    (client_id,),
                )
                row = cursor.fetchone()
                if row:
                    first_name = (row["first_name"] or "").strip()
                    last_name = (row["last_name"] or "").strip()
                    return {
                        "name": f"{first_name} {last_name}".strip() or client_id,
                        "budget": 0,
                        "needs": [],
                        "current_housing": row["housing_status"] or "unknown",
                        "move_in_date": None
                    }
        except Exception:
            pass

        return {
            "name": client_id,
            "budget": 0,
            "needs": [],
            "current_housing": "unknown",
            "move_in_date": None
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response for case manager"""
        return {
            "success": False,
            "error": error_message,
            "case_manager_view": True,
            "suggested_actions": [
                "Try a different search term",
                "Check if the housing search service is running",
                "Contact system administrator"
            ]
        }

# Global instance for use in routes
case_manager_tools = CaseManagerHousingTools()

async def enhanced_case_manager_search(query, location, client_id=None, client_budget=None, client_needs=None):
    """Legacy function wrapper for the new case manager tools"""
    return await case_manager_tools.enhanced_case_manager_search(
        query=query,
        location=location,
        client_id=client_id,
        client_budget=client_budget,
        client_needs=client_needs
    )

# Legacy functions for backward compatibility
def generate_quick_actions(result):
    """Generate quick actions for case managers"""
    return case_manager_tools._generate_quick_actions(result, None)

def calculate_client_match(result, budget, needs):
    """Score how well this matches client needs"""
    return case_manager_tools._calculate_client_match_score(result, budget, needs)

def extract_price_from_title(result):
    """Extract price from result title"""
    prices = case_manager_tools._extract_prices_from_text(result.get('title', ''))
    return min(prices) if prices else 0

def prioritize_for_case_managers(results):
    """Prioritize results for case managers"""
    return case_manager_tools._prioritize_for_case_managers(results, None, None)

def extract_contact_info(result):
    """Extract contact information"""
    return case_manager_tools._extract_contact_info(result)

# Case manager dashboard configuration
HOUSING_DASHBOARD_FOR_CM = {
    "quick_searches": [
        "1BR under $1200 Los Angeles",
        "2BR pet friendly Hollywood", 
        "Studio downtown LA under $1000",
        "accessible housing Los Angeles"
    ],
    "saved_resources": [
        "LA Housing Authority waitlist",
        "Section 8 approved landlords",
        "Emergency housing contacts",
        "Client housing application templates"
    ],
    "client_housing_tracker": {
        "pending_applications": [],
        "scheduled_viewings": [],
        "housing_placed": [],
        "follow_up_needed": []
    }
}
