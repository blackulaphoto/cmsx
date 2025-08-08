"""
Simple Search Module - Bullet-proof unified search layer
"""

from .coordinator import get_coordinator, SearchType, SearchResult

# Lazy initialization - don't create instance during import
def get_search_coordinator():
    """Get the search coordinator instance (lazy initialization)"""
    return get_coordinator()

# For backward compatibility, provide the function
search_coordinator = get_search_coordinator

__all__ = ['search_coordinator', 'SearchType', 'SearchResult'] 