import httpx
from typing import List, Dict, Any, Optional

class OpenAlexClient:
    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, email: Optional[str] = None):
        self.email = email  # For identifying requests to OpenAlex "polite pool"

    async def search_works(self, query: str, issn_list: List[str], limit: int = 0, sort: str = "cited_by_count:desc") -> tuple[List[Dict[str, Any]], bool]:
        """
        Search OpenAlex for works matching the query, restricted to the given ISSNs.
        
        Args:
            limit: Max results. 0 means 'All' (up to MAX_RESULTS cap).
        
        Returns:
            Tuple of (results_list, has_more_flag).
            has_more_flag is True if there were more results than MAX_RESULTS.
        """
        MAX_RESULTS = 2000  # Circuit breaker
        
        if not issn_list:
            return [], False

        safe_issns = issn_list[:50] 
        issn_filter = "|".join(safe_issns)
        
        params = {
            "filter": f"primary_location.source.issn:{issn_filter}",
            "sort": sort,
        }
        
        if query and query.strip() != "*":
            params["search"] = query

        if self.email:
            params["mailto"] = self.email

        # Determine effective limit
        effective_limit = limit if limit > 0 else MAX_RESULTS
        effective_limit = min(effective_limit, MAX_RESULTS)  # Never exceed cap

        async with httpx.AsyncClient() as client:
            try:
                all_results = []
                per_page = 200
                params["per_page"] = per_page
                
                import math
                max_pages = math.ceil(effective_limit / per_page)

                has_more = False
                for page in range(1, max_pages + 1):
                    params["page"] = page
                    
                    resp = await client.get(self.BASE_URL, params=params, timeout=30.0)
                    resp.raise_for_status()
                    data = resp.json()
                    results = data.get('results', [])
                    total_count = data.get('meta', {}).get('count', 0)
                    
                    if not results:
                        break
                        
                    all_results.extend(results)
                    
                    # Check if API has more than we can return
                    if total_count > MAX_RESULTS:
                        has_more = True
                    
                    if len(all_results) >= effective_limit:
                        all_results = all_results[:effective_limit]
                        break
                
                return all_results, has_more

            except Exception as e:
                print(f"OpenAlex API Error: {e}")
                return [], False
