import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hybrid_retrieval import reciprocal_rank_fusion


def chunk(identifier, text=None):
    return {"id": identifier, "text": text or identifier, "source_id": "s", "source": "s",
            "page": 1, "metadata": {}, "score": 0.5}


class FusionTests(unittest.TestCase):
    def test_shared_candidate_accumulates_rank_contributions(self):
        result = reciprocal_rank_fusion({"dense": [chunk("a"), chunk("b")],
                                         "tfidf": [chunk("b"), chunk("c")]}, k=60)
        self.assertEqual([c["id"] for c in result], ["b", "a", "c"])
        self.assertAlmostEqual(result[0]["score"], 1 / 62 + 1 / 61)
        self.assertEqual(result[0]["component_ranks"], {"dense": 2, "tfidf": 1})

    def test_rejects_inconsistent_shared_chunk(self):
        with self.assertRaises(ValueError):
            reciprocal_rank_fusion({"dense": [chunk("a")], "tfidf": [chunk("a", "changed")]})


if __name__ == "__main__":
    unittest.main()
