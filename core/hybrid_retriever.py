from services.pinecone_service import query_pinecone
from retrievers.bm25_retriever import BM25Retriever


class HybridRetriever:
    def __init__(self, embedding_service, documents):
        self.embedding = embedding_service
        self.bm25 = BM25Retriever(documents)

    def retrieve(self, query, categories=None, top_k=5):
        # 1. Vector search
        vector = self.embedding.embed(query)

        vector_results = query_pinecone(
            vector=vector,
            top_k=top_k,
            categories=categories
        )

        # 2. BM25 search
        bm25_results = self.bm25.search(query, top_k)

        # 3. Merge
        merged = self._merge(vector_results, bm25_results)

        return merged

    def _merge(self, vec_results, bm25_results):
        combined = vec_results + bm25_results

        seen = set()
        unique = []

        for item in combined:
            if item["text"] not in seen:
                seen.add(item["text"])
                unique.append(item)

        return unique