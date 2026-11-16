"""Export one Day 6 pgvector collection as Day 7 chunk records, read-only."""

import argparse
import json
from pathlib import Path

import psycopg
from dotenv import dotenv_values


def validate_chunks(chunks):
    """Check the Day 7 contract before writing an export."""
    if not chunks:
        raise ValueError("No chunks found for the requested strategy.")
    ids = set()
    for chunk in chunks:
        for key in ("id", "source_id", "source", "text"):
            if not isinstance(chunk[key], str) or not chunk[key].strip():
                raise ValueError(f"Invalid or empty {key} in exported chunk.")
        if chunk["id"] in ids:
            raise ValueError("Duplicate chunk ID in export.")
        ids.add(chunk["id"])
        if type(chunk["page"]) is not int or chunk["page"] < 1:
            raise ValueError("Invalid physical PDF page in exported chunk.")
        if not isinstance(chunk["metadata"], dict):
            raise ValueError("Chunk metadata must be a JSON object.")


def export_chunks(database_url, strategy):
    """Read stable chunk fields; do not change the database or expose its URL."""
    with psycopg.connect(database_url) as connection:
        rows = connection.execute(
            """SELECT chunk_id, document_id, source, page, content, metadata
               FROM day6_chunks WHERE strategy = %s ORDER BY chunk_id""",
            (strategy,),
        ).fetchall()
    chunks = [dict(zip(("id", "source_id", "source", "page", "text", "metadata"), row))
              for row in rows]
    validate_chunks(chunks)
    return chunks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day6-env", type=Path, required=True,
                        help="Path to the local Day 6 .env; never share this file.")
    parser.add_argument("--output", type=Path, required=True,
                        help="New JSON file; existing files are never overwritten.")
    parser.add_argument("--strategy", default="history_B", help="Day 6 strategy (default: history_B).")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new path to avoid overwriting it.")
    if not args.day6_env.is_file():
        raise SystemExit("Day 6 .env file not found.")
    url = dotenv_values(args.day6_env).get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing.")
    try:
        chunks = export_chunks(url, args.strategy)
    except psycopg.Error:
        raise SystemExit("Database query failed. Check the Day 6 service and connection settings.") from None
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(chunks, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(f"Exported {len(chunks)} chunks from {args.strategy} to {args.output}")


if __name__ == "__main__":
    main()
