from tavily import TavilyClient
import os

key = "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"
tavily = TavilyClient(api_key=key)
print("Searching...")
try:
    search_results = tavily.search(query="What is RAG?", max_results=3)
    print("Results:", search_results)
except Exception as e:
    print("Error:", e)
