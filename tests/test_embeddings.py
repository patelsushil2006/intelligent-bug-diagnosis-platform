from knowledge_base.embeddings import EmbeddingEngine


def test_embedding_generation():
    engine = EmbeddingEngine()
    texts = [
        "NullPointerException in StringUtils.join",
        "ModuleNotFoundError: No module named 'flask'"
    ]
    vectors = engine.embed_texts(texts)
    assert len(vectors) == 2
    assert len(vectors[0]) == 384  # Standard all-MiniLM-L6-v2 dimension


def test_query_embedding():
    engine = EmbeddingEngine()
    query_vec = engine.embed_query("TypeError: cannot read property of undefined")
    assert len(query_vec) == 384
    assert isinstance(query_vec[0], float)
