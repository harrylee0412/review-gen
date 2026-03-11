
import pandas as pd
from typing import List, Dict, Any
from openalex_mcp.utils import reconstruct_abstract

def generate_excel_report(works: List[Dict[str, Any]], output_path: str):
    """
    Generate an Excel report from OpenAlex works.
    Columns: Journal, Year, Title, Authors, Citations, Abstract, DOI
    """
    rows = []
    
    for work in works:
        # Extract fields
        title = work.get('title', 'No Title')
        year = work.get('publication_year', '')
        cited_by = work.get('cited_by_count', 0)
        doi = work.get('doi', '')
        
        # Source
        source = work.get('primary_location', {}).get('source', {}) or {}
        journal = source.get('display_name', 'Unknown Journal')
        
        # Authors (First 3 et al)
        authors = [a.get('author', {}).get('display_name', '') for a in work.get('authorships', [])]
        authors_str = ", ".join(authors)
        
        # Abstract
        abstract = ""
        inverted = work.get('abstract_inverted_index')
        if inverted:
            abstract = reconstruct_abstract(inverted)
            
        rows.append({
            "Journal": journal,
            "Year": year,
            "Title": title,
            "Authors": authors_str,
            "Citations": cited_by,
            "DOI": doi,
            "Abstract": abstract
        })
        
    df = pd.DataFrame(rows)
    
    # Sort by Citations descending
    df = df.sort_values(by="Citations", ascending=False)
    
    # Save
    df.to_excel(output_path, index=False)
    return len(df)
