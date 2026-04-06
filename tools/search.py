import os
from tavily import TavilyClient

SEARCH_SCHEMA = {
    "name": "search",
    "description": "Search the web for current information on a topic. Returns top 3 results with title, URL, and content.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            }
        },
        "required": ["query"],
    },
}


def search(query: str) -> str:
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))
    results = client.search(query, max_results=3)
    parts = []
    for r in results["results"]:
        parts.append(f"**{r['title']}**\n{r['url']}\n{r['content']}")
    return "\n---\n".join(parts)
