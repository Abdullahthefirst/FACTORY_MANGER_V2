"""Gemini embedding helpers used by the optional RAG assistant."""

from google.genai import types


EMBEDDING_MODEL = "gemini-embedding-001"


def embed_documents(client, texts):
    if not texts:
        return []

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
        ),
    )

    return [item.values for item in response.embeddings]


def embed_query(client, text):
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[text],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
        ),
    )

    return response.embeddings[0].values
