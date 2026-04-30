"""
SPARQL query syntax validator using rdflib's built-in parser.
"""

import logging

from rdflib.plugins.sparql import prepareQuery

logger = logging.getLogger(__name__)


def validate_sparql(query: str) -> tuple[bool, str]:
    """
    Validate SPARQL query syntax.

    Returns:
        (is_valid, error_message)
    """
    try:
        prepareQuery(query)
        return True, ""
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"SPARQL validation failed: {error_msg}")
        return False, error_msg


def clean_sparql_response(text: str) -> str:
    """
    Clean LLM output to extract pure SPARQL query.
    Removes markdown code blocks and extra text.
    """
    text = text.strip()

    # Remove markdown code blocks
    if text.startswith("```") and text.endswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]).strip()
    elif text.startswith("```sparql"):
        text = text[len("```sparql") :]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    elif text.startswith("```"):
        text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    return text
