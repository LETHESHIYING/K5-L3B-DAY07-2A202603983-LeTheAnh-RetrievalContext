"""Run a read-only dense/TF-IDF/RRF practice comparison with Day 6 data."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))
from baseline import TfidfIndex  # noqa: E402
from hybrid_retrieval import reciprocal_rank_fusion  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day6-starter", type=Path, required=True)
    parser.add_argument("--chunks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--candidates", type=int, default=3)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--rrf-k", type=int, default=60)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new path.")
    if args.candidates < args.top_k or args.top_k < 1 or args.rrf_k < 0:
        raise SystemExit("Require candidates >= top-k >= 1 and rrf-k >= 0.")

    # Day 6 has a separate src package. Import its adapters after loading Day 7 modules.
    sys.path.insert(0, str(args.day6_starter.resolve()))
    from dotenv import dotenv_values
    from src.embeddings import MyEmbedder
    from src.store import PgVectorStore
    import psycopg

    url = dotenv_values(args.day6_starter / ".env").get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL missing from Day 6 .env")
    chunks = json.loads(args.chunks.read_text(encoding="utf-8"))
    if not chunks or len({c["id"] for c in chunks}) != len(chunks):
        raise SystemExit("Chunk file is empty or has duplicate IDs.")
    with psycopg.connect(url) as conn:
        rows = conn.execute("""SELECT chunk_id, document_id, source, page, content, metadata
                               FROM day6_chunks WHERE strategy = %s ORDER BY chunk_id""",
                            ("history_B",)).fetchall()
    keys = ("id", "source_id", "source", "page", "text", "metadata")
    if [dict(zip(keys, row)) for row in rows] != sorted(chunks, key=lambda c: c["id"]):
        raise SystemExit("Export and database differ; regenerate or investigate before comparing.")
    model = MyEmbedder()
    index = TfidfIndex(chunks)
    start = time.perf_counter()
    raw = PgVectorStore(url, model.dimensions).search(
        "history_B", model.embed_query(args.query), top_k=args.candidates)
    dense = [{"id": x["chunk_id"], "source_id": x["document_id"],
              **{key: x[key] for key in ("source", "page", "text", "metadata", "score")}}
             for x in raw]
    dense_seconds = time.perf_counter() - start
    start = time.perf_counter()
    lexical = index.search(args.query, top_k=args.candidates)
    lexical_seconds = time.perf_counter() - start
    start = time.perf_counter()
    hybrid = reciprocal_rank_fusion({"dense": dense, "tfidf": lexical},
                                    k=args.rrf_k, top_k=args.top_k)
    fusion_seconds = time.perf_counter() - start
    trace = {"purpose": "practice, not benchmark", "query": args.query,
             "strategy": "history_B", "filters": {}, "candidate_depth": args.candidates,
             "top_k": args.top_k, "rrf_k": args.rrf_k, "model": model.model_name,
             "model_revision": model.revision, "dimensions": model.dimensions,
             "corpus_matches_database": True,
             "seconds_excluding_model_and_index_load": {"dense": dense_seconds,
                 "tfidf": lexical_seconds, "fusion_only": fusion_seconds},
             "dense": dense, "tfidf": lexical, "hybrid": hybrid}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(trace, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(f"Saved practice trace: {args.output}")
    for rank, chunk in enumerate(hybrid, 1):
        print(f"{rank}. page={chunk['page']} RRF={chunk['score']:.6f} ranks={chunk['component_ranks']}")


if __name__ == "__main__":
    main()
