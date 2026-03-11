from typing import List, Dict, Any

def reconstruct_abstract(inverted_index: Dict[str, List[int]]) -> str:
    """
    Reconstruct abstract from OpenAlex inverted index.
    The index maps "word" -> [list of positions].
    """
    if not inverted_index:
        return ""
    
    # Create a list big enough to hold all words
    # Find max position
    max_pos = 0
    for pos_list in inverted_index.values():
        for pos in pos_list:
            if pos > max_pos:
                max_pos = pos
                
    # Fill array
    words = [""] * (max_pos + 1)
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
            
    return " ".join(words)

def work_to_ris_entry(work: Dict[str, Any]) -> str:
    """
    Convert a single OpenAlex work object to an RIS entry string.
    """
    entry = []
    entry.append("TY  - JOUR") # Assume journal article for now
    
    # Title
    title = work.get('title', 'No Title')
    entry.append(f"TI  - {title}")
    
    # Authors
    for authorship in work.get('authorships', []):
        author_name = authorship.get('author', {}).get('display_name')
        if author_name:
            entry.append(f"AU  - {author_name}")
            
    # Journal / Source
    loc = work.get('primary_location', {}) or {}
    source = loc.get('source', {}) or {}
    if source:
        entry.append(f"JO  - {source.get('display_name', '')}")
        entry.append(f"SN  - {source.get('issn_l', '')}")
        
    # Pub Year
    entry.append(f"PY  - {work.get('publication_year', '')}")
    
    # Volume/Issue/Pages
    biblio = work.get('biblio', {})
    if biblio.get('volume'): entry.append(f"VL  - {biblio.get('volume')}")
    if biblio.get('issue'): entry.append(f"IS  - {biblio.get('issue')}")
    if biblio.get('first_page'): 
        end = biblio.get('last_page', '')
        entry.append(f"SP  - {biblio.get('first_page')}")
        if end: entry.append(f"EP  - {end}")
    
    # DOI and URL
    doi = work.get('doi', '')
    if doi:
        entry.append(f"DO  - {doi.replace('https://doi.org/', '')}")
        entry.append(f"UR  - {doi}")
    
    # Abstract
    inverted = work.get('abstract_inverted_index')
    if inverted:
        abstract_text = reconstruct_abstract(inverted)
        # Check constraints? RIS usually fine with long text
        entry.append(f"AB  - {abstract_text}")
    
    entry.append("ER  -")
    return "\n".join(entry)

def works_to_ris_block(works: List[Dict[str, Any]]) -> str:
    """
    Convert a list of works to a full RIS block.
    """
    return "\n\n".join([work_to_ris_entry(w) for w in works])
