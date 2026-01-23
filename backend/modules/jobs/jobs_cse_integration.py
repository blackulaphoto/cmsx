# backend/search/coordinator.py - Update your existing coordinator

class SimpleSearchCoordinator:
    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        
        # Services CSE (original)
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        
        # NEW: Jobs-specific CSE
        self.google_jobs_cse_id = os.getenv("GOOGLE_JOBS_CSE_ID", "b5088b7b14bdb4f11")
        
        logger.info(f"🔑 Google API Key: {'✅ Loaded' if self.google_api_key else '❌ Missing'}")
        logger.info(f"🔍 Services CSE ID: {'✅ Loaded' if self.google_cse_id else '❌ Missing'}")
        logger.info(f"💼 Jobs CSE ID: {'✅ Loaded' if self.google_jobs_cse_id else '❌ Missing'}")

    async def search_jobs(self, query: str, location: str = None, limit: int = 10):
        """Search for jobs using dedicated Jobs CSE"""
        try:
            # Use the dedicated jobs CSE
            cse_id = self.google_jobs_cse_id
            
            # Enhanced query for better job results
            enhanced_query = query
            if location:
                enhanced_query = f"{query} {location}"
            
            # Add job-specific keywords to improve relevance
            job_keywords = "employment career position hiring"
            enhanced_query = f"{enhanced_query} {job_keywords}"
            
            logger.info(f"🔍 Jobs search: '{enhanced_query}' using CSE: {cse_id}")
            
            # Perform search with jobs CSE
            results = await self._perform_google_search(
                query=enhanced_query,
                cse_id=cse_id,
                limit=limit
            )
            
            # Same formatting as before - no routing changes needed
            return {
                "success": True,
                "query": query,
                "location": location,
                "results": results,
                "source": "google_jobs_cse",
                "total_results": len(results)
            }
            
        except Exception as e:
            logger.error(f"Jobs search error: {e}")
            # Fallback to original CSE if jobs CSE fails
            return await self._fallback_jobs_search(query, location, limit)
    
    async def _fallback_jobs_search(self, query: str, location: str = None, limit: int = 10):
        """Fallback to original CSE if jobs CSE fails"""
        logger.warning("🔄 Falling back to original CSE for jobs search")
        
        enhanced_query = f"{query} jobs employment"
        if location:
            enhanced_query = f"{enhanced_query} {location}"
            
        results = await self._perform_google_search(
            query=enhanced_query,
            cse_id=self.google_cse_id,  # Original CSE
            limit=limit
        )
        
        return {
            "success": True,
            "query": query,
            "location": location,
            "results": results,
            "source": "google_general_cse_fallback",
            "total_results": len(results)
        }

    async def search_services(self, query: str, location: str = None, limit: int = 10):
        """Search for services using original CSE"""
        try:
            # Use original CSE for services
            cse_id = self.google_cse_id
            
            enhanced_query = query
            if location:
                enhanced_query = f"{query} {location}"
            
            # Add service-specific keywords
            service_keywords = "therapy counseling medical benefits social services"
            enhanced_query = f"{enhanced_query} {service_keywords}"
            
            logger.info(f"🔍 Services search: '{enhanced_query}' using CSE: {cse_id}")
            
            results = await self._perform_google_search(
                query=enhanced_query,
                cse_id=cse_id,
                limit=limit
            )
            
            return {
                "success": True,
                "query": query,
                "location": location,
                "results": results,
                "source": "google_services_cse",
                "total_results": len(results)
            }
            
        except Exception as e:
            logger.error(f"Services search error: {e}")
            return {"success": False, "error": str(e)}

    async def _perform_google_search(self, query: str, cse_id: str, limit: int = 10):
        """Common Google search logic - no changes needed"""
        # Your existing search logic here
        # Just pass the appropriate cse_id parameter
        pass