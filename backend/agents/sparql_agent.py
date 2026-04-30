"""
SPARQL Agent — Converts natural language questions into SPARQL queries,
validates them, executes on the local ontology.

Inspired by the sql_agent pattern: generator → validator → executor
with automatic retry on errors.
"""

import logging
from dataclasses import dataclass, field

from openai import OpenAI

from backend.agents.prompts import SPARQL_GENERATOR_PROMPT
from backend.config import MAX_SPARQL_RETRIES, OPENAI_API_KEY, OPENAI_MODEL
from backend.services.ontology_service import OntologyService
from backend.utils.result_formatter import format_results_summary
from backend.utils.sparql_validator import clean_sparql_response, validate_sparql

logger = logging.getLogger(__name__)


@dataclass
class SPARQLAgentState:
    """State tracked across the agent's execution steps."""

    user_question: str
    sparql_query: str = ""
    results: list[dict] = field(default_factory=list)
    result_summary: dict = field(default_factory=dict)
    error: str = ""
    retry_count: int = 0
    previous_queries: list[str] = field(default_factory=list)
    success: bool = False


class SPARQLAgent:
    """
    Agent that converts natural language to SPARQL, validates, executes,
    and explains results. Retries on failure.
    """

    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Set it before starting the server."
            )
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.max_retries = MAX_SPARQL_RETRIES
        self.ontology_schema = OntologyService.get_ontology_schema()

    def run(self, question: str) -> SPARQLAgentState:
        """
        Agent pipeline: generate → validate → execute.
        Retries up to max_retries on errors.
        """
        state = SPARQLAgentState(user_question=question)

        for attempt in range(self.max_retries + 1):
            state.retry_count = attempt

            # Step 1: Generate SPARQL
            logger.info(f"[Attempt {attempt + 1}] Generating SPARQL query...")
            state = self._generate_sparql(state)

            if not state.sparql_query:
                state.error = "Failed to generate SPARQL query"
                continue

            # Step 2: Validate syntax
            logger.info(f"[Attempt {attempt + 1}] Validating SPARQL syntax...")
            is_valid, validation_error = validate_sparql(state.sparql_query)

            if not is_valid:
                logger.warning(
                    f"[Attempt {attempt + 1}] Validation failed: {validation_error}"
                )
                state.error = f"Syntax error: {validation_error}"
                state.previous_queries.append(state.sparql_query)
                continue

            # Step 3: Execute query
            logger.info(f"[Attempt {attempt + 1}] Executing SPARQL query...")
            state = self._execute_query(state)

            if state.error:
                logger.warning(
                    f"[Attempt {attempt + 1}] Execution error: {state.error}"
                )
                state.previous_queries.append(state.sparql_query)
                continue

            # Step 4: Check for empty results
            if not state.results:
                logger.warning(f"[Attempt {attempt + 1}] Query returned 0 results")
                state.error = (
                    "Query returned 0 results. Try broadening the search criteria."
                )
                state.previous_queries.append(state.sparql_query)
                if attempt < self.max_retries:
                    continue
                break

            # Success!
            state.success = True
            state.error = ""
            break

        return state

    def _generate_sparql(self, state: SPARQLAgentState) -> SPARQLAgentState:
        """Use LLM to generate a SPARQL query from natural language."""
        # Build context about previous attempts
        previous_attempts = ""
        if state.previous_queries:
            prev_text = "\n\n".join(
                f"Attempt {i + 1}:\n{q}" for i, q in enumerate(state.previous_queries)
            )
            previous_attempts = (
                f"PREVIOUS FAILED ATTEMPTS (avoid these mistakes):\n{prev_text}"
            )

        error_feedback = ""
        if state.error:
            error_feedback = (
                f"THE PREVIOUS QUERY FAILED WITH THIS ERROR:\n{state.error}\n"
                "Fix this issue in the new query."
            )

        prompt = SPARQL_GENERATOR_PROMPT.format(
            ontology_schema=self.ontology_schema,
            user_question=state.user_question,
            previous_attempts=previous_attempts,
            error_feedback=error_feedback,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a SPARQL query expert. Return ONLY valid SPARQL queries, nothing else.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
            )

            raw = response.choices[0].message.content or ""
            state.sparql_query = clean_sparql_response(raw)
            logger.info(f"Generated SPARQL:\n{state.sparql_query}")

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            state.error = f"LLM error: {str(e)}"
            state.sparql_query = ""

        return state

    def _execute_query(self, state: SPARQLAgentState) -> SPARQLAgentState:
        """Execute the SPARQL query on the local ontology."""
        try:
            results = OntologyService.execute_sparql(state.sparql_query)
            state.results = results
            state.result_summary = format_results_summary(results)
            state.error = ""
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            state.error = f"Execution error: {str(e)}"
            state.results = []

        return state
