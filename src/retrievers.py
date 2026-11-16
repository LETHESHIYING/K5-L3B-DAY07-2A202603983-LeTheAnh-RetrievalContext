"""Real Day 6 dense, TF-IDF and RRF retrieval adapters."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starter'))
from baseline import TfidfIndex
from hybrid_retrieval import reciprocal_rank_fusion


class RetrievalEngine:
    def __init__(self, chunks, embedder, store, strategy='history_B'):
        self.embedder, self.store, self.strategy = embedder, store, strategy
        self.lexical = TfidfIndex(chunks)

    def search(self, query, *, method, top_k=3, candidate_depth=10, rrf_k=60):
        if method not in ('dense', 'tfidf', 'hybrid') or top_k < 1:
            raise ValueError('Invalid retrieval method or top_k')
        if candidate_depth < top_k:
            raise ValueError('candidate_depth must be at least top_k')
        dense, lexical = [], []
        if method in ('dense', 'hybrid'):
            raw = self.store.search(self.strategy, self.embedder.embed_query(query),
                                    top_k=candidate_depth if method == 'hybrid' else top_k)
            dense = [{'id': c['chunk_id'], 'source_id': c['document_id'],
                      **{key: c[key] for key in ('source', 'page', 'text', 'metadata', 'score')}}
                     for c in raw]
        if method in ('tfidf', 'hybrid'):
            lexical = self.lexical.search(query, top_k=candidate_depth if method == 'hybrid' else top_k)
        if method == 'dense':
            return dense
        if method == 'tfidf':
            return lexical
        return reciprocal_rank_fusion({'dense': dense, 'tfidf': lexical}, k=rrf_k, top_k=top_k)
