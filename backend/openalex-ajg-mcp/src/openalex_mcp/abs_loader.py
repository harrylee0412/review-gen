
import pandas as pd
from typing import List, Optional
import importlib.resources
import os

class ABSCache:
    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize ABS Cache.
        If csv_path is None, loads the bundled 'ajg_2024_template.csv' from package data.
        """
        self.df = None
        self.csv_path = csv_path
        self._load_data()

    def _load_data(self):
        try:
            if self.csv_path and os.path.exists(self.csv_path):
                # User provided custom path
                self.df = pd.read_csv(self.csv_path)
            else:
                # Load bundled data from package
                # Use importlib.resources.files (Python 3.9+)
                pkg_files = importlib.resources.files("openalex_mcp.data")
                with importlib.resources.as_file(pkg_files / "ajg_2024_template.csv") as f:
                    self.df = pd.read_csv(f)

            # Ensure data types
            if self.df is not None:
                self.df['ISSN'] = self.df['ISSN'].astype(str).str.strip()
                self.df['Rank'] = self.df['Rank'].astype(str).str.strip()
                self.df['Field'] = self.df['Field'].astype(str).str.strip()
                
        except Exception as e:
            print(f"Error loading ABS data: {e}")
            self.df = pd.DataFrame(columns=["Journal Title", "ISSN", "Field", "Rank"])

    def get_issns(self, field: Optional[str] = None, min_rank: Optional[str] = None) -> List[str]:
        if self.df is None or self.df.empty:
            return []

        filtered = self.df

        if field:
            filtered = filtered[filtered['Field'].str.upper() == field.upper()]

        if min_rank:
            if min_rank == "4":
                filtered = filtered[filtered['Rank'].isin(["4", "4*"])]
            elif min_rank == "3":
                filtered = filtered[filtered['Rank'].isin(["3", "4", "4*"])]
            else:
                filtered = filtered[filtered['Rank'] == min_rank]

        issns = set()
        for raw_issn in filtered['ISSN'].dropna():
            parts = [x.strip() for x in raw_issn.replace(';', ',').split(',')]
            issns.update(parts)
            
        return list(issns)
