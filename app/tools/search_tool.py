"""
search_tool.py — Mock web search tool (Phase 1 + Phase 2).

Phase 1 behaviour is unchanged when called without a scenario config:
  - known keywords → matching results
  - unknown query  → fallback generic result

Phase 2 adds controlled failure injection via an optional
ToolFailureConfig passed in by the agent.  The config is never
part of the LLM-visible tool schema.

Failure modes (driven by ToolFailureConfig):
  empty_result=True    → status "success" but results=[]
                         (used for empty_result and loop scenarios)
"""

from __future__ import annotations

from app.scenarios.config import ToolFailureConfig

# ---------------------------------------------------------------------------
# Deterministic mock data
# ---------------------------------------------------------------------------
MOCK_SEARCH_RESULTS: dict[str, list[dict]] = {
    "python programming": [
        {
            "title": "Python Official Documentation",
            "url": "https://docs.python.org/3/",
            "snippet": (
                "Python is a high-level, interpreted, general-purpose programming language. "
                "Its design philosophy emphasises code readability with the use of significant indentation."
            ),
        },
        {
            "title": "Python Tutorial — W3Schools",
            "url": "https://www.w3schools.com/python/",
            "snippet": (
                "Python is a popular programming language used for web development, data science, "
                "artificial intelligence, and automation."
            ),
        },
        {
            "title": "Real Python — Tutorials and Articles",
            "url": "https://realpython.com/",
            "snippet": (
                "Real Python provides practical Python tutorials, articles, and courses "
                "for developers at all skill levels."
            ),
        },
    ],
    "machine learning": [
        {
            "title": "Machine Learning — Wikipedia",
            "url": "https://en.wikipedia.org/wiki/Machine_learning",
            "snippet": (
                "Machine learning is a subset of AI that gives systems the ability to "
                "automatically learn and improve from experience without being explicitly programmed."
            ),
        },
        {
            "title": "Scikit-learn: Machine Learning in Python",
            "url": "https://scikit-learn.org/",
            "snippet": (
                "Scikit-learn provides simple and efficient tools for predictive data analysis, "
                "built on NumPy, SciPy, and matplotlib."
            ),
        },
    ],
    "groq api": [
        {
            "title": "Groq — Fast AI Inference",
            "url": "https://groq.com/",
            "snippet": (
                "Groq provides ultra-fast LLM inference using its LPU™ Inference Engine. "
                "It offers an OpenAI-compatible API for running models like Llama and Mixtral."
            ),
        },
        {
            "title": "Groq API Documentation",
            "url": "https://console.groq.com/docs/",
            "snippet": (
                "Learn how to use the Groq API to run LLMs at high speed. "
                "Supports tool/function calling, streaming, and chat completions."
            ),
        },
    ],
    "artificial intelligence": [
        {
            "title": "Artificial Intelligence — Wikipedia",
            "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "snippet": (
                "Artificial intelligence (AI) is the simulation of human intelligence by machines, "
                "especially computer systems, covering learning, reasoning, and self-correction."
            ),
        },
        {
            "title": "AI Research — OpenAI",
            "url": "https://openai.com/research/",
            "snippet": (
                "OpenAI conducts research on artificial intelligence with a focus on safe and "
                "beneficial AI systems."
            ),
        },
    ],
    "hyderabad": [
        {
            "title": "Hyderabad — Wikipedia",
            "url": "https://en.wikipedia.org/wiki/Hyderabad",
            "snippet": (
                "Hyderabad is the capital city of Telangana, India, known as the 'City of Pearls'. "
                "It is a major tech hub home to companies like Microsoft, Google, and Amazon."
            ),
        },
        {
            "title": "Tourism in Hyderabad",
            "url": "https://www.telangana.gov.in/tourism",
            "snippet": (
                "Hyderabad is famous for the Charminar, Golconda Fort, Ramoji Film City, "
                "and its world-renowned biryani."
            ),
        },
    ],
}

# Generic fallback used when no keyword matches in normal (Phase 1) mode.
FALLBACK_RESULT = [
    {
        "title": "Search Results — No Specific Data Available",
        "url": "https://www.example.com/search",
        "snippet": (
            "No specific mock data found for this query. "
            "In a real system, this would fetch live search results."
        ),
    }
]


def _find_results(query: str) -> list[dict]:
    """Return results for the best matching keyword in the query."""
    query_lower = query.lower()
    for keyword, results in MOCK_SEARCH_RESULTS.items():
        if keyword in query_lower:
            return results
    return FALLBACK_RESULT


# ---------------------------------------------------------------------------
# Public tool function
# ---------------------------------------------------------------------------

def search_tool(
    query: str,
    _scenario: ToolFailureConfig | None = None,
) -> dict:
    """
    Perform a mock web search for the given query.

    Args:
        query:     The search query string.
        _scenario: Optional ToolFailureConfig injected by the agent.
                   NOT exposed in the LLM tool schema.

    Returns:
        A dict with:
          - status: "success"
          - query: the original query
          - results: list of result dicts (may be empty in Phase 2)
          - message: human-readable summary
    """
    # ── Phase 2: empty result injection ──────────────────────────────
    if _scenario is not None and _scenario.empty_result:
        return {
            "status": "success",
            "query": query,
            "results": [],
            "message": (
                f"Search completed for '{query}' but returned no results. "
                "The topic may not be indexed or may not exist."
            ),
        }

    # ── Phase 1 / normal path ─────────────────────────────────────────
    results = _find_results(query)

    return {
        "status": "success",
        "query": query,
        "results": results,
        "message": (
            f"Found {len(results)} result(s) for '{query}'. "
            "Top result: " + results[0]["title"] + "."
        ),
    }
