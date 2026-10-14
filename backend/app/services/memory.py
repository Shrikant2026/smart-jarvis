import uuid

import chromadb
from chromadb.utils import embedding_functions

from app.core.config import CHROMA_PATH

CHROMA_PATH.mkdir(parents=True, exist_ok=True)

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_PATH)
)

embedding_function = (
    embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
)

collection = chroma_client.get_or_create_collection(
    name="jarvis_memory",
    embedding_function=embedding_function,
)


def store_memory(text: str, source: str = "chat") -> str:
    memory_id = str(uuid.uuid4())

    collection.add(
        documents=[text],
        metadatas=[{"source": source}],
        ids=[memory_id],
    )

    return memory_id


def search_memory(query: str, n_results: int = 5) -> list[str]:
    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
    )

    return results["documents"][0] or []


def get_memory(query: str) -> list[str]:
    return search_memory(query, n_results=3)