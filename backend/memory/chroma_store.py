"""ChromaDB wrapper: save_memory, search_memory.

Provides persistent vector storage for all agent outputs.
Uses the singleton embedder from embeddings.py.
"""

import chromadb
import hashlib
import time
from memory.embeddings import embedder

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("atlas_memory")


def save_memory(content: str, metadata: dict) -> None:
    """Save a piece of content to ChromaDB with metadata."""
    embedding = embedder.encode(content).tolist()
    doc_id = hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()
    metadata["timestamp"] = str(time.time())
    collection.add(
        documents=[content],
        embeddings=[embedding],
        metadatas=[metadata],
        ids=[doc_id],
    )


def search_memory(query: str, n: int = 5, filter_agent: str = None) -> list[str]:
    """Search ChromaDB for memories similar to query.

    Args:
        query: The search text.
        n: Max number of results to return.
        filter_agent: If provided, only return memories from this agent.

    Returns:
        List of matching document strings.
    """
    embedding = embedder.encode(query).tolist()
    where = {"agent": filter_agent} if filter_agent else None
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n,
        where=where,
    )
    return results["documents"][0] if results["documents"] else []
