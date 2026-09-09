"""Small session-only vector index for the optional RAG chatbot."""

import numpy as np

from src.ai.embeddings import embed_documents, embed_query


def build_index(client, documents):
    if not documents:
        return {"documents": [], "vectors": []}

    vectors = embed_documents(client, documents)
    return {
        "documents": documents,
        "vectors": np.asarray(vectors, dtype=float),
    }


def retrieve(client, index, question, limit=6):
    if not index or not index.get("documents"):
        return []

    query_vector = np.asarray(
        embed_query(client, question),
        dtype=float,
    )

    vectors = index["vectors"]
    vector_norms = np.linalg.norm(vectors, axis=1)
    query_norm = np.linalg.norm(query_vector)
    denominator = vector_norms * query_norm

    scores = np.divide(
        vectors @ query_vector,
        denominator,
        out=np.zeros_like(vector_norms),
        where=denominator != 0,
    )

    ranked = np.argsort(scores)[::-1][:limit]

    return [
        {
            "text": index["documents"][int(position)],
            "score": float(scores[position]),
        }
        for position in ranked
    ]
