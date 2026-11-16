"""Reciprocal rank fusion for Day 7 retrieval candidates."""


def reciprocal_rank_fusion(rankings, *, k=60, top_k=3):
    """Fuse named rankings of Day 7 chunks; retain component ranks and scores."""
    if k < 0 or top_k < 1:
        raise ValueError("k must be nonnegative and top_k must be positive")
    combined = {}
    for name, results in rankings.items():
        seen = set()
        for rank, chunk in enumerate(results, start=1):
            chunk_id = chunk["id"]
            if chunk_id in seen:
                raise ValueError(f"Duplicate chunk ID in {name} ranking")
            seen.add(chunk_id)
            if chunk_id not in combined:
                combined[chunk_id] = {**chunk, "score": 0.0, "component_ranks": {},
                                      "component_scores": {}}
            item = combined[chunk_id]
            for field in ("text", "source_id", "source", "page", "metadata"):
                if item[field] != chunk[field]:
                    raise ValueError(f"Chunk mismatch between rankings: {chunk_id}")
            item["score"] += 1 / (k + rank)
            item["component_ranks"][name] = rank
            item["component_scores"][name] = chunk.get("score")
    return sorted(combined.values(), key=lambda item: (-item["score"], item["id"]))[:top_k]
