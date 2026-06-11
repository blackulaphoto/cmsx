#!/usr/bin/env python3
"""
Simple Housing Tools - What case managers actually do
Sober living homes + housing assistance programs (NOT apartment hunting)
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class HousingResourceTools:
    """Query Virgil St database for ACTUAL housing resources case managers use"""

    def __init__(self, db_path: str = None):
        _repo_db = Path(__file__).resolve().parents[3] / "databases" / "virgil_st_dev.db"
        self.db_path = db_path or str(_repo_db)
        self.connection = None

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Connected to housing database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to housing database: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def search_sober_living(
        self,
        gender: Optional[str] = None,
        city: Optional[str] = None,
        accepts_medi_cal: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Search sober living homes - what case managers actually look up
        """
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()

            # Build WHERE clause
            where_clauses = ["type = 'sober_living'", "isPublished = 1"]
            params = []

            if gender:
                if gender.lower() in ['men', 'male', 'm']:
                    where_clauses.append("servesPopulation = 'men'")
                elif gender.lower() in ['women', 'female', 'f']:
                    where_clauses.append("servesPopulation = 'women'")
                elif gender.lower() in ['coed', 'both', 'all']:
                    where_clauses.append("servesPopulation = 'coed'")

            if city:
                where_clauses.append("LOWER(city) LIKE ?")
                params.append(f"%{city.lower()}%")

            if accepts_medi_cal:
                where_clauses.append("acceptsMediCal = 1")

            where_sql = " AND ".join(where_clauses)

            # Count total results
            count_sql = f"SELECT COUNT(*) FROM treatment_centers WHERE {where_sql}"
            cursor.execute(count_sql, params)
            total_results = cursor.fetchone()[0]

            # Get paginated results
            offset = (page - 1) * per_page
            sql = f"""
                SELECT id, name, type, address, city, zipCode, phone, website,
                       servesPopulation, acceptsMediCal, acceptsMedicare,
                       acceptsPrivateInsurance, priceRange, description,
                       servicesOffered, amenities
                FROM treatment_centers
                WHERE {where_sql}
                ORDER BY name
                LIMIT ? OFFSET ?
            """

            cursor.execute(sql, params + [per_page, offset])
            rows = cursor.fetchall()

            results = []
            for row in rows:
                # Parse services and amenities
                services = row['servicesOffered'].split(',') if row['servicesOffered'] else []
                amenities = row['amenities'].split(',') if row['amenities'] else []

                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'address': f"{row['address']}, {row['city']}, CA {row['zipCode']}" if row['address'] else f"{row['city']}, CA",
                    'phone': row['phone'] or 'Contact for details',
                    'website': row['website'] or '',
                    'serves': row['servesPopulation'].title(),
                    'payment_options': {
                        'medi_cal': bool(row['acceptsMediCal']),
                        'medicare': bool(row['acceptsMedicare']),
                        'private_insurance': bool(row['acceptsPrivateInsurance']),
                        'price_range': row['priceRange'] or 'Contact for pricing'
                    },
                    'description': row['description'] or f"Sober living home for {row['servesPopulation']}",
                    'services': [s.strip() for s in services if s.strip()],
                    'amenities': [a.strip() for a in amenities if a.strip()],
                    'type': 'Sober Living Home'
                })

            total_pages = max(1, (total_results + per_page - 1) // per_page)

            return {
                'success': True,
                'results': results,
                'total_count': total_results,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_results': total_results,
                    'total_pages': total_pages,
                    'has_next_page': page < total_pages,
                    'has_prev_page': page > 1,
                }
            }

        except sqlite3.OperationalError as e:
            logger.warning(f"Sober living DB table not available: {e}")
            return {
                'success': True,
                'results': [],
                'total_count': 0,
                'pagination': {
                    'current_page': page, 'per_page': per_page,
                    'total_results': 0, 'total_pages': 1,
                    'has_next_page': False, 'has_prev_page': False,
                },
            }
        except Exception as e:
            logger.error(f"Sober living search error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'total_count': 0
            }

    def search_housing_programs(
        self,
        keywords: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Search housing assistance programs - Section 8, vouchers, etc.
        """
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()

            where_clauses = ["type = 'housing'"]
            params = []

            if keywords:
                where_clauses.append("(LOWER(name) LIKE ? OR LOWER(description) LIKE ?)")
                search_pattern = f"%{keywords.lower()}%"
                params.extend([search_pattern, search_pattern])

            where_sql = " AND ".join(where_clauses)

            # Count total
            count_sql = f"SELECT COUNT(*) FROM resources WHERE {where_sql}"
            cursor.execute(count_sql, params)
            total_results = cursor.fetchone()[0]

            # Get results
            offset = (page - 1) * per_page
            sql = f"""
                SELECT id, name, description, address, phone, website, hours
                FROM resources
                WHERE {where_sql}
                ORDER BY name
                LIMIT ? OFFSET ?
            """

            cursor.execute(sql, params + [per_page, offset])
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'] or 'Housing assistance program',
                    'address': row['address'] or 'Los Angeles County',
                    'phone': row['phone'] or 'Contact for details',
                    'website': row['website'] or '',
                    'hours': row['hours'] or 'Contact for hours',
                    'type': 'Housing Assistance Program'
                })

            total_pages = max(1, (total_results + per_page - 1) // per_page)

            return {
                'success': True,
                'results': results,
                'total_count': total_results,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_results': total_results,
                    'total_pages': total_pages,
                    'has_next_page': page < total_pages,
                    'has_prev_page': page > 1,
                }
            }

        except sqlite3.OperationalError as e:
            logger.warning(f"Housing programs DB table not available: {e}")
            return {
                'success': True,
                'results': [],
                'total_count': 0,
                'pagination': {
                    'current_page': page, 'per_page': per_page,
                    'total_results': 0, 'total_pages': 1,
                    'has_next_page': False, 'has_prev_page': False,
                },
            }
        except Exception as e:
            logger.error(f"Housing programs search error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'total_count': 0
            }


def get_housing_search_urls(keywords: str = "affordable housing", location: str = "Los Angeles") -> Dict[str, str]:
    """
    Generate housing search URLs (if clients want to apartment hunt themselves)
    """
    from urllib.parse import urlencode, quote_plus

    return {
        'apartments_com': f"https://www.apartments.com/{location.lower().replace(' ', '-')}-ca/",
        'zillow_rentals': f"https://www.zillow.com/homes/{location.replace(' ', '-')}-CA_rb/",
        'craigslist': f"https://losangeles.craigslist.org/search/apa?query={quote_plus(keywords)}",
        'hotpads': f"https://hotpads.com/{location.lower().replace(' ', '-')}-ca",
        'note': 'Most case managers do NOT apartment hunt for clients - focus on sober living and housing assistance programs instead'
    }


# Singleton instance
_housing_tools = None

def get_housing_tools() -> HousingResourceTools:
    """Get singleton housing tools instance"""
    global _housing_tools
    if _housing_tools is None:
        _housing_tools = HousingResourceTools()
    return _housing_tools
