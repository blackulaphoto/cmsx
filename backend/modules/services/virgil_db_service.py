#!/usr/bin/env python3
"""
Virgil St Database Service - Query the integrated service database
Combines resources, treatment_centers, medi_cal_providers, and meetings
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re

logger = logging.getLogger(__name__)

class VirgilServiceDatabase:
    """Query service data from virgil_st_dev.db"""

    def __init__(self, db_path: str = "databases/virgil_st_dev.db"):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Connected to Virgil St database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to Virgil St database: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def _map_service_type_to_category(self, service_type: str) -> str:
        """Map Virgil St service types to CMSX categories"""
        type_mapping = {
            'shelter': 'housing',
            'housing': 'housing',
            'sober_living': 'housing',
            'residential': 'substance-abuse',
            'outpatient': 'substance-abuse',
            'detox': 'substance-abuse',
            'food': 'support-groups',
            'dental': 'mental-health',
            'hygiene': 'support-groups',
            'legal': 'education',
            'transportation': 'transportation',
            'couples_counseling': 'mental-health',
            'parenting_classes': 'education',
        }
        return type_mapping.get(service_type, 'all')

    def _build_search_conditions(self, query: str) -> Tuple[str, List[str]]:
        """Build SQL WHERE conditions from search query"""
        query_lower = query.lower().strip()

        # Extract key search terms
        search_terms = []

        # Category-based searches
        if any(term in query_lower for term in ['mental', 'health', 'therapy', 'counseling', 'psychiatric']):
            search_terms.append('mental')
            search_terms.append('health')
        if any(term in query_lower for term in ['substance', 'abuse', 'addiction', 'recovery', 'detox', 'rehab']):
            search_terms.append('substance')
            search_terms.append('recovery')
        if any(term in query_lower for term in ['housing', 'shelter', 'sober living', 'residential']):
            search_terms.append('housing')
            search_terms.append('shelter')
        if any(term in query_lower for term in ['food', 'meal', 'nutrition']):
            search_terms.append('food')
        if any(term in query_lower for term in ['dental', 'dentist', 'teeth']):
            search_terms.append('dental')
        if any(term in query_lower for term in ['legal', 'lawyer', 'attorney']):
            search_terms.append('legal')
        if any(term in query_lower for term in ['transport', 'bus', 'metro', 'ride']):
            search_terms.append('transport')
        if any(term in query_lower for term in ['meeting', 'aa', 'na', 'support group']):
            search_terms.append('meeting')

        # Generic queries - show all services
        if any(term in query_lower for term in ['social services', 'all services', 'services']):
            # Return empty to trigger "show all" mode
            return []

        # If no specific category, use the actual query terms
        if not search_terms:
            # Split query into individual words
            search_terms = [word for word in query_lower.split() if len(word) > 2]

        return search_terms

    def _normalize_category(self, category: Optional[str]) -> Optional[str]:
        if not category:
            return None
        normalized = category.strip().lower()
        return normalized if normalized and normalized != 'all' else None

    def _normalize_population(self, population: Optional[str]) -> Optional[str]:
        if not population:
            return None
        normalized = population.strip().lower()
        mapping = {
            'men': 'men',
            'women': 'women',
            'co-ed': 'coed',
            'coed': 'coed',
            'couples': 'couples',
        }
        return mapping.get(normalized)

    def _normalize_insurance_type(self, insurance_type: Optional[str]) -> Optional[str]:
        if not insurance_type:
            return None
        normalized = insurance_type.strip().lower()
        mapping = {
            'medi-cal': 'medi-cal',
            'medical': 'medi-cal',
            'private': 'private',
            'private insurance': 'private',
        }
        return mapping.get(normalized)

    def _category_filters(self, category: Optional[str]) -> Dict[str, Any]:
        normalized = self._normalize_category(category)
        category_map = {
            'mental-health': {
                'resource_types': {'couples_counseling'},
                'treatment_types': set(),
                'meeting_types': set(),
                'include_medical': True,
                'medical_terms': ['psychiatry', 'mental', 'behavior', 'counsel', 'therapy'],
            },
            'substance-abuse': {
                'resource_types': set(),
                'treatment_types': {'residential', 'outpatient'},
                'meeting_types': {'aa', 'na', 'smart', 'cma'},
                'include_medical': False,
                'medical_terms': [],
            },
            'housing': {
                'resource_types': {'housing', 'shelter'},
                'treatment_types': {'sober_living'},
                'meeting_types': set(),
                'include_medical': False,
                'medical_terms': [],
            },
            'transportation': {
                'resource_types': {'transportation'},
                'treatment_types': set(),
                'meeting_types': set(),
                'include_medical': False,
                'medical_terms': [],
            },
            'education': {
                'resource_types': {'parenting_classes', 'legal'},
                'treatment_types': set(),
                'meeting_types': set(),
                'include_medical': False,
                'medical_terms': [],
            },
            'support-groups': {
                'resource_types': {'food', 'hygiene'},
                'treatment_types': set(),
                'meeting_types': {'aa', 'na', 'smart', 'cma'},
                'include_medical': False,
                'medical_terms': [],
            },
        }
        return category_map.get(normalized, {
            'resource_types': set(),
            'treatment_types': set(),
            'meeting_types': set(),
            'include_medical': False,
            'medical_terms': [],
        })

    def _score_result_for_category(self, result: Dict[str, Any], category: Optional[str]) -> Tuple[int, str]:
        normalized = self._normalize_category(category)
        source = result.get('source', '')
        service_type = (result.get('service_type') or '').lower()

        if normalized == 'substance-abuse':
            if source == 'virgil_st_treatment':
                return (0, result.get('title', ''))
            if source == 'virgil_st_meetings':
                return (1, result.get('title', ''))
        elif normalized == 'support-groups':
            if source == 'virgil_st_meetings':
                return (0, result.get('title', ''))
            if 'support group' in service_type:
                return (1, result.get('title', ''))
        elif normalized == 'mental-health':
            if 'mental health' in service_type or 'psychi' in result.get('description', '').lower():
                return (0, result.get('title', ''))
            if source == 'virgil_st_medical':
                return (1, result.get('title', ''))
        elif normalized == 'housing':
            if 'housing' in service_type or 'shelter' in service_type:
                return (0, result.get('title', ''))
            if 'sober living' in service_type:
                return (1, result.get('title', ''))
        elif normalized == 'transportation':
            if 'transportation' in service_type:
                return (0, result.get('title', ''))

        return (5, result.get('title', ''))

    def search_services(
        self,
        query: str,
        location: str = None,
        page: int = 1,
        per_page: int = 10,
        category: Optional[str] = None,
        population: Optional[str] = None,
        insurance_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search across all service tables (resources, treatment_centers, medi_cal_providers, meetings)
        """
        if not self.connection:
            self.connect()

        try:
            search_terms = self._build_search_conditions(query)
            normalized_category = self._normalize_category(category)
            normalized_population = self._normalize_population(population)
            normalized_insurance = self._normalize_insurance_type(insurance_type)
            category_filters = self._category_filters(normalized_category)
            all_results = []
            treatment_filter_active = bool(normalized_population or normalized_insurance)

            has_category_filter = bool(normalized_category)
            include_resources = not has_category_filter or bool(category_filters['resource_types'])
            include_treatment = not has_category_filter or bool(category_filters['treatment_types'])
            include_meetings = not treatment_filter_active and (
                bool(category_filters['meeting_types']) or any(
                term in query.lower() for term in ['meeting', 'aa', 'na', 'support', 'group']
                )
            )

            # 1. Search resources table
            if include_resources:
                resources = self._search_resources(search_terms, location, normalized_category, category_filters)
                all_results.extend(resources)

            # 2. Search treatment_centers table
            if include_treatment:
                treatment_centers = self._search_treatment_centers(
                    search_terms,
                    location,
                    normalized_category,
                    category_filters,
                    population=normalized_population,
                    insurance_type=normalized_insurance,
                )
                all_results.extend(treatment_centers)

            # 3. Search medi_cal_providers table (for mental health/medical queries)
            should_include_medical = category_filters['include_medical'] or any(
                term in query.lower() for term in ['mental', 'health', 'doctor', 'medical', 'provider', 'clinic']
            )
            if should_include_medical:
                medi_cal = self._search_medi_cal_providers(search_terms, location, normalized_category, category_filters)
                all_results.extend(medi_cal)

            # 4. Search meetings table (for AA/NA/support groups)
            if include_meetings:
                meetings = self._search_meetings(search_terms, location, normalized_category, category_filters)
                all_results.extend(meetings)

            # Remove obvious duplicates and prioritize category-relevant rows first.
            deduped_results = []
            seen = set()
            for result in all_results:
                dedupe_key = (
                    (result.get('title') or '').strip().lower(),
                    (result.get('address') or '').strip().lower(),
                    (result.get('service_type') or '').strip().lower(),
                )
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                deduped_results.append(result)

            deduped_results.sort(key=lambda item: self._score_result_for_category(item, normalized_category))

            # Paginate results
            total_results = len(deduped_results)
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            paginated_results = deduped_results[start_index:end_index]

            # Calculate pagination metadata
            total_pages = max(1, (total_results + per_page - 1) // per_page)

            return {
                'success': True,
                'results': paginated_results,
                'total_count': total_results,
                'source': 'virgil_st_db',
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_results': total_results,
                    'total_pages': total_pages,
                    'has_next_page': page < total_pages,
                    'has_prev_page': page > 1,
                    'start_index': start_index + 1 if total_results > 0 else 0,
                    'end_index': min(end_index, total_results)
                }
            }

        except Exception as e:
            logger.error(f"Virgil St DB search error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'total_count': 0,
                'pagination': {
                    'current_page': 1,
                    'per_page': per_page,
                    'total_results': 0,
                    'total_pages': 0,
                    'has_next_page': False,
                    'has_prev_page': False,
                    'start_index': 0,
                    'end_index': 0
                }
            }

    def _search_resources(self, search_terms: List[str], location: str = None, category: Optional[str] = None, category_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search the resources table"""
        cursor = self.connection.cursor()

        # Build WHERE clause
        where_clauses = []
        params = []

        category_filters = category_filters or self._category_filters(category)
        resource_types = category_filters.get('resource_types') or set()

        if resource_types:
            type_clause = " OR ".join(["LOWER(type) = ?"] * len(resource_types))
            where_clauses.append(f"({type_clause})")
            params.extend(sorted(resource_types))

        if search_terms:  # Specific search
            term_clauses = []
            for term in search_terms:
                term_clauses.append("(LOWER(name) LIKE ? OR LOWER(type) LIKE ? OR LOWER(description) LIKE ?)")
                search_pattern = f"%{term}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            where_clauses.append(f"({' OR '.join(term_clauses)})")

        if where_clauses:
            where_sql = " AND ".join(where_clauses)
        else:  # Show all
            where_sql = "1=1"

        sql = f"""
            SELECT id, name, type, description, address, phone, website, hours,
                   zipCode, latitude, longitude, isVerified
            FROM resources
            WHERE {where_sql}
            LIMIT 100
        """

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                'title': row['name'],
                'description': row['description'] or f"{row['type'].replace('_', ' ').title()} service",
                'link': row['website'] or '',
                'url': row['website'] or '',
                'address': row['address'] or location or 'Los Angeles, CA',
                'phone': row['phone'] or 'Contact for details',
                'location': row['address'] or location or 'Los Angeles, CA',
                'service_type': row['type'].replace('_', ' ').title() if row['type'] else 'General Services',
                'source': 'virgil_st_resources',
                'relevance_reason': f"Matches {row['type']} services in your area",
                'background_friendly_score': 70,  # Most social services are background-friendly
            })

        return results

    def _search_treatment_centers(
        self,
        search_terms: List[str],
        location: str = None,
        category: Optional[str] = None,
        category_filters: Optional[Dict[str, Any]] = None,
        population: Optional[str] = None,
        insurance_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search the treatment_centers table"""
        cursor = self.connection.cursor()

        where_clauses = []
        params = []

        category_filters = category_filters or self._category_filters(category)
        treatment_types = category_filters.get('treatment_types') or set()

        if treatment_types:
            type_clause = " OR ".join(["LOWER(type) = ?"] * len(treatment_types))
            where_clauses.append(f"({type_clause})")
            params.extend(sorted(treatment_types))

        if population:
            where_clauses.append("LOWER(COALESCE(servesPopulation, '')) = ?")
            params.append(population)

        if insurance_type == 'medi-cal':
            where_clauses.append("acceptsMediCal = 1")
        elif insurance_type == 'private':
            where_clauses.append("acceptsPrivateInsurance = 1")

        if search_terms:  # Specific search
            term_clauses = []
            for term in search_terms:
                term_clauses.append("(LOWER(name) LIKE ? OR LOWER(type) LIKE ? OR LOWER(description) LIKE ? OR LOWER(servicesOffered) LIKE ?)")
                search_pattern = f"%{term}%"
                params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
            where_clauses.append(f"({' OR '.join(term_clauses)})")

        if where_clauses:
            where_sql = " AND ".join(where_clauses)
        else:  # Show all
            where_sql = "1=1"

        sql = f"""
            SELECT id, name, type, description, address, city, zipCode, phone, website,
                   servesPopulation, acceptsMediCal, acceptsMedicare, acceptsPrivateInsurance,
                   servicesOffered, amenities, priceRange
            FROM treatment_centers
            WHERE ({where_sql}) AND isPublished = 1
            LIMIT 100
        """

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            # Build description
            desc_parts = []
            if row['description']:
                desc_parts.append(row['description'])
            if row['servicesOffered']:
                desc_parts.append(f"Services: {row['servicesOffered']}")
            if row['acceptsMediCal']:
                desc_parts.append("Accepts Medi-Cal")
            if row['acceptsMedicare']:
                desc_parts.append("Accepts Medicare")

            description = '. '.join(desc_parts) if desc_parts else f"{row['type'].replace('_', ' ').title()} treatment center"

            results.append({
                'title': row['name'],
                'description': description,
                'link': row['website'] or '',
                'url': row['website'] or '',
                'address': f"{row['address']}, {row['city']}, CA {row['zipCode']}" if row['address'] else (location or 'Los Angeles, CA'),
                'phone': row['phone'] or 'Contact for details',
                'location': f"{row['city']}, CA" if row['city'] else (location or 'Los Angeles, CA'),
                'service_type': f"{row['type'].replace('_', ' ').title()} - {row['servesPopulation'].title()}",
                'source': 'virgil_st_treatment',
                'relevance_reason': f"{row['type'].replace('_', ' ').title()} treatment facility serving {row['servesPopulation']}",
                'background_friendly_score': 75,
                'serves_population': row['servesPopulation'] or '',
                'accepts_medi_cal': bool(row['acceptsMediCal']),
                'accepts_private_insurance': bool(row['acceptsPrivateInsurance']),
                'accepts_medicare': bool(row['acceptsMedicare']),
            })

        return results

    def _search_medi_cal_providers(self, search_terms: List[str], location: str = None, category: Optional[str] = None, category_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search the medi_cal_providers table"""
        cursor = self.connection.cursor()

        where_clauses = []
        params = []

        category_filters = category_filters or self._category_filters(category)
        medical_terms = category_filters.get('medical_terms') or []

        if medical_terms:
            specialty_clauses = []
            for term in medical_terms:
                specialty_clauses.append("LOWER(specialties) LIKE ?")
                params.append(f"%{term}%")
            where_clauses.append(f"({' OR '.join(specialty_clauses)})")

        if search_terms:  # Specific search
            term_clauses = []
            for term in search_terms:
                term_clauses.append("(LOWER(providerName) LIKE ? OR LOWER(facilityName) LIKE ? OR LOWER(specialties) LIKE ?)")
                search_pattern = f"%{term}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            where_clauses.append(f"({' OR '.join(term_clauses)})")
        elif not medical_terms:  # Don't show all medi-cal providers by default (too many)
            return []

        where_sql = " AND ".join(where_clauses)

        sql = f"""
            SELECT id, providerName, facilityName, address, city, zipCode, phone,
                   specialties, gender, languagesSpoken, networks
            FROM medi_cal_providers
            WHERE {where_sql}
            LIMIT 50
        """

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            name = row['facilityName'] or row['providerName']
            desc_parts = [row['providerName']]
            if row['specialties']:
                desc_parts.append(f"Specialties: {row['specialties']}")
            if row['languagesSpoken']:
                desc_parts.append(f"Languages: {row['languagesSpoken']}")

            results.append({
                'title': name,
                'description': '. '.join(desc_parts),
                'link': '',
                'url': '',
                'address': f"{row['address']}, {row['city']}, CA {row['zipCode']}" if row['address'] else (location or 'Los Angeles, CA'),
                'phone': row['phone'] or 'Contact for details',
                'location': f"{row['city']}, CA" if row['city'] else (location or 'Los Angeles, CA'),
                'service_type': 'Medical/Mental Health Provider',
                'source': 'virgil_st_medical',
                'relevance_reason': 'Medi-Cal provider in your area',
                'background_friendly_score': 80,
            })

        return results

    def _search_meetings(self, search_terms: List[str], location: str = None, category: Optional[str] = None, category_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search the meetings table"""
        cursor = self.connection.cursor()

        where_clauses = []
        params = []

        category_filters = category_filters or self._category_filters(category)
        meeting_types = category_filters.get('meeting_types') or set()

        if meeting_types:
            type_clause = " OR ".join(["LOWER(type) = ?"] * len(meeting_types))
            where_clauses.append(f"({type_clause})")
            params.extend(sorted(meeting_types))

        if search_terms:  # Specific search
            term_clauses = []
            for term in search_terms:
                term_clauses.append("(LOWER(name) LIKE ? OR LOWER(type) LIKE ? OR LOWER(format) LIKE ? OR LOWER(tags) LIKE ?)")
                search_pattern = f"%{term}%"
                params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
            where_clauses.append(f"({' OR '.join(term_clauses)})")

        if where_clauses:
            where_sql = " AND ".join(where_clauses)
        else:  # Show all meetings for generic search
            where_sql = "1=1"

        sql = f"""
            SELECT id, name, type, dayOfWeek, time, duration, venueName, address, city, zipCode,
                   format, meetingMode, zoomId, description, notes
            FROM meetings
            WHERE ({where_sql}) AND isPublished = 1
            LIMIT 50
        """

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            meeting_info = []
            meeting_info.append(f"{row['type']} meeting")
            meeting_info.append(f"{row['dayOfWeek']} at {row['time']}")
            meeting_info.append(f"{row['format']} - {row['meetingMode']}")
            if row['description']:
                meeting_info.append(row['description'])

            location_str = row['venueName'] or row['address'] or location or 'Los Angeles, CA'
            if row['city']:
                location_str = f"{location_str}, {row['city']}, CA"

            results.append({
                'title': row['name'],
                'description': '. '.join(meeting_info),
                'link': '',
                'url': '',
                'address': location_str,
                'phone': 'Check meeting details',
                'location': location_str,
                'service_type': f"{row['type']} Support Group",
                'source': 'virgil_st_meetings',
                'relevance_reason': f"{row['type']} {row['format']} meeting on {row['dayOfWeek']}",
                'background_friendly_score': 95,  # Support groups are very background-friendly
            })

        return results

# Singleton instance
_virgil_db = None

def get_virgil_db() -> VirgilServiceDatabase:
    """Get or create singleton Virgil St database instance"""
    global _virgil_db
    if _virgil_db is None:
        _virgil_db = VirgilServiceDatabase()
    return _virgil_db
