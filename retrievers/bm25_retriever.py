from rank_bm25 import BM25Okapi
import numpy as np


class BM25Retriever:
    def __init__(self, documents):
        self.documents = documents

        self.tokenized_corpus = [
            doc["text"].lower().split()
            for doc in documents
        ]

        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def search(self, query, top_k=5):
        tokenized_query = query.lower().split()

        scores = self.bm25.get_scores(tokenized_query)

        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append({
                "text": self.documents[idx]["text"],
                "score": float(scores[idx]),
                "source": "bm25"
            })

        return results