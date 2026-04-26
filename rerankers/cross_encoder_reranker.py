from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    def __init__(self):
        self.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def rerank(self, query, chunks, top_k=3):
        pairs = [(query, c["text"]) for c in chunks]

        scores = self.model.predict(pairs)

        scored = []
        for chunk, score in zip(chunks, scores):
            scored.append({
                **chunk,
                "rerank_score": float(score)
            })

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)

        return scored[:top_k]