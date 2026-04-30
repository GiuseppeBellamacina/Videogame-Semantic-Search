"""
Utilities for formatting SPARQL query results.
"""


def format_results_summary(results: list[dict]) -> dict:
    """
    Analyze and summarize query results.
    """
    total_rows = len(results)

    if total_rows == 0:
        return {
            "total_rows": 0,
            "is_empty": True,
            "columns": [],
            "preview": [],
        }

    columns = list(results[0].keys()) if results else []

    # Create a preview with first 10 rows
    preview = results[:10]

    return {
        "total_rows": total_rows,
        "is_empty": False,
        "columns": columns,
        "preview": preview,
    }
