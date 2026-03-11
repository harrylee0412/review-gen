from mcp.server.fastmcp import FastMCP
from openalex_mcp.abs_loader import ABSCache
from openalex_mcp.client import OpenAlexClient
from openalex_mcp.utils import works_to_ris_block, reconstruct_abstract
from openalex_mcp.report_generator import generate_excel_report
import pandas as pd
import os
import locale

mcp = FastMCP("openalex-abs-search")

# Initialize Cache with bundled data (default) or environment override
ABS_DATA_PATH = os.getenv("MCP_ABS_DATA_PATH", None) 
abs_cache = ABSCache(ABS_DATA_PATH)
client = OpenAlexClient() 

@mcp.tool()
async def search_abs_literature(
    query: str, 
    field: str = "", 
    min_rank: str = "3", 
    limit: int = 0, 
    year_start: int = 2024,
    export: bool = False,
    lang: str = "auto"
) -> str:
    """
    Search for literature in ABS-ranked journals.
    
    Args:
        query: Search keywords.
        field: ABS Field Code (e.g. 'MKT', 'ENT-SBM'). Leave empty to search ALL ABS journals (includes general management journals like AMJ, AMR).
        min_rank: Minimum rank ('3', '4', '4*').
        limit: Max results (0 = All, up to 2000).
        year_start: Start year.
        export: Whether to generate Excel/RIS files.
        lang: Output language ('cn', 'en', 'auto').
    """
    is_cn = (lang == "cn") or (lang == "auto" and any('\u4e00' <= char <= '\u9fff' for char in query))

    # Get ISSNs - if field is empty, search all ABS journals
    search_field = field.strip() if field else None
    issns = abs_cache.get_issns(field=search_field, min_rank=min_rank)
    if not issns:
        if search_field:
            msg = f"未找到领域 '{field}' 且等级>='{min_rank}' 的期刊。" if is_cn else f"No journals found for Field='{field}' and Rank>='{min_rank}'."
        else:
            msg = f"未找到等级>='{min_rank}' 的期刊。" if is_cn else f"No journals found for Rank>='{min_rank}'."
        return msg

    # Search OpenAlex (Sort by publication date desc to get recent ones)
    sort_param = "publication_date:desc"
    works, has_more = await client.search_works(query, issns, limit=limit, sort=sort_param)
    
    # Client filter might be broad, filter by year strictly
    filtered_works = [w for w in works if w.get('publication_year', 0) >= year_start]
    
    count = len(filtered_works)
    if count == 0:
        return "未找到符合条件的文献。" if is_cn else "No papers found matching criteria."

    summary = ""
    field_display = search_field if search_field else ("所有领域" if is_cn else "ALL Fields")
    if is_cn:
        summary = f"已找到 **{count}** 篇文献 (领域: {field_display}, 等级: {min_rank}+, 年份: {year_start}+)。\n"
        if has_more:
            summary += "⚠️ **注意**: 符合条件的文献超过 2000 篇，请缩小搜索范围（如提高期刊等级、缩短年份范围或添加关键词）。\n"
    else:
        summary = f"Found **{count}** papers (Field: {field_display}, Rank: {min_rank}+, Year: {year_start}+).\n"
        if has_more:
            summary += "⚠️ **Note**: More than 2000 results exist. Please narrow your search (e.g., increase rank, shorten year range, or add keywords).\n"

    if export:
        base_dir = os.getcwd() 
        field_for_filename = search_field if search_field else "ALL"
        excel_filename = f"report_{field_for_filename}_{min_rank}.xlsx"
        excel_path = os.path.join(base_dir, excel_filename)
        generate_excel_report(filtered_works, excel_path)
        
        ris_filename = f"citations_{field_for_filename}_{min_rank}.ris"
        ris_path = os.path.join(base_dir, ris_filename)
        ris_content = works_to_ris_block(filtered_works)
        with open(ris_path, "w", encoding="utf-8") as f:
            f.write(ris_content)

        if is_cn:
            summary += f"文件已导出:\n- Excel: `{excel_path}`\n- RIS: `{ris_path}`\n\n您可以使用 `summarize_literature_report` 工具对导出的文件进行总结。"
        else:
            summary += f"Files exported:\n- Excel: `{excel_path}`\n- RIS: `{ris_path}`\n\nYou can use `summarize_literature_report` to generate a summary."
    else:
         if is_cn:
             summary += "如果需要详细列表和导出文件，请将 `export` 参数设置为 `True` 并再次运行。"
         else:
             summary += "To generate Excel/RIS files, run again with `export=True`."

    return summary

@mcp.tool()
async def search_journal_literature(
    journal_name: str,
    query: str,
    year_start: int = 2024,
    limit: int = 0,
    export: bool = False,
    lang: str = "auto"
) -> str:
    """
    Search for literature in a specific journal.
    
    Args:
        journal_name: Name or abbreviation of the journal (e.g. 'Journal of Business Venturing').
        query: Search keywords.
        year_start: Start year.
        limit: Max results.
        export: Whether to generate Excel/RIS files.
        lang: Output language.
    """
    is_cn = (lang == "cn") or (lang == "auto" and any('\u4e00' <= char <= '\u9fff' for char in journal_name + query))
    
    # 1. Try to resolve ISSN effectively. 
    # Since we have a local ABS Cache, let's search there first for precision.
    # Note: ABS Cache stores 'Journal Title'.
    
    # We need to expose a search method in ABSCache or do it here. 
    # Accessing private df directy for MVP.
    journal_issn = None
    resolved_name = journal_name
    
    if abs_cache.df is not None:
        # Simple case insensitive match
        matches = abs_cache.df[abs_cache.df['Journal Title'].str.contains(journal_name, case=False, regex=False)]
        if not matches.empty:
            # Pick first match or exact match
            # Priority: Exact match -> First match
            exact = matches[matches['Journal Title'].str.lower() == journal_name.lower()]
            start_row = exact.iloc[0] if not exact.empty else matches.iloc[0]
            
            raw_issn = str(start_row['ISSN']).strip()
            # Handle multiple ISSNs "xxxx-xxxx; yyyy-yyyy"
            parts = [x.strip() for x in raw_issn.replace(';', ',').split(',')]
            journal_issn = parts[0] if parts else None
            resolved_name = start_row['Journal Title']
    
    # If not found in local cache, we could ask OpenAlex /sources, but let's rely on cached ABS for now as per context.
    if not journal_issn:
        msg = f"未能在 ABS 列表中找到期刊 '{journal_name}'。请尝试使用全称或检查拼写。" if is_cn else f"Journal '{journal_name}' not found in ABS list. Please check spelling."
        return msg

    # 2. Search
    # Reuse client but with single ISSN
    sort_param = "publication_date:desc"
    works, has_more = await client.search_works(query, [journal_issn], limit=limit, sort=sort_param)
    
    filtered_works = [w for w in works if w.get('publication_year', 0) >= year_start]
    count = len(filtered_works)
    
    summary = ""
    if is_cn:
        summary = f"在 **{resolved_name}** 中找到 **{count}** 篇文献 (年份: {year_start}+)。\n"
        if has_more:
            summary += "⚠️ **注意**: 符合条件的文献超过 2000 篇，请缩小搜索范围。\n"
    else:
        summary = f"Found **{count}** papers in **{resolved_name}** (Year: {year_start}+).\n"
        if has_more:
            summary += "⚠️ **Note**: More than 2000 results exist. Please narrow your search.\n"
        
    if count == 0:
        return summary

    if export:
        base_dir = os.getcwd()
        # Sanitize filename
        safe_name = "".join([c for c in resolved_name if c.isalnum() or c in (' ','-','_')]).strip().replace(' ', '_')
        excel_path = os.path.join(base_dir, f"report_{safe_name}.xlsx")
        ris_path = os.path.join(base_dir, f"citations_{safe_name}.ris")
        
        generate_excel_report(filtered_works, excel_path)
        ris_content = works_to_ris_block(filtered_works)
        with open(ris_path, "w", encoding="utf-8") as f:
            f.write(ris_content)
            
        if is_cn:
            summary += f"文件已导出:\n- Excel: `{excel_path}`\n- RIS: `{ris_path}`\n\n可以使用 `summarize_literature_report` 进行总结。"
        else:
            summary += f"Files exported:\n- Excel: `{excel_path}`\n- RIS: `{ris_path}`\n"
    else:
        if is_cn:
            summary += "需要导出请设置 `export=True`。"
        else:
            summary += "Set `export=True` to save files."
            
    return summary

@mcp.tool()
def summarize_literature_report(file_path: str, lang: str = "auto") -> str:
    """
    Generate a summary from an exported Excel report.
    
    Args:
        file_path: Absolute path to the Excel file.
        lang: Output language.
    """
    if not os.path.exists(file_path):
        return f"File not found: {file_path}"
        
    # Heuristic for lang
    is_cn = (lang == "cn")
    
    try:
        df = pd.read_excel(file_path)
        if df.empty:
            return "文件为空。" if is_cn else "File is empty."
            
        count = len(df)
        years = df['Year'].value_counts().sort_index()
        top_cited = df.sort_values(by='Citations', ascending=False).head(5)
        
        # Determine strict top authors
        # Author format from report_generator is ", " joined names (no institutions)
        all_authors = []
        for authors_str in df['Authors'].dropna().astype(str):
            # split by comma
            u_authors = authors_str.split(', ')
            for au in u_authors:
                name = au.strip()
                if name:
                    all_authors.append(name)
        
        from collections import Counter
        top_authors = Counter(all_authors).most_common(5)
        
        md = f"## 📊 文献汇总报告\n\n" if is_cn else f"## 📊 Literature Summary Report\n\n"
        md += f"- **Total Papers**: {count}\n"
        # Handle case where min/max might be nan if file is weird
        min_year = df['Year'].min()
        max_year = df['Year'].max()
        md += f"- **Years Range**: {min_year} - {max_year}\n\n"
        
        md += "### 📅 年份分布 (Yearly Distribution)\n"
        for y, c in years.items():
            md += f"- {y}: {c}\n"
            
        md += "\n### ✍️ 活跃作者 (Top Authors)\n"
        for name, c in top_authors:
            md += f"- {name}: {c}\n"
            
        md += "\n### ⭐ 高引论文 (Top Cited)\n"
        for _, row in top_cited.iterrows():
            title = row.get('Title', 'No Title')
            c = row.get('Citations', 0)
            y = row.get('Year', '')
            md += f"- [{y}] **{title}** (Citations: {c})\n"
            
        return md

    except Exception as e:
        return f"Error analyzing report: {e}"

def main():
    mcp.run()
