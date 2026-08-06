from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.benchmark.record_human_review import ingest_human_review


class HumanReviewIngestTests(unittest.TestCase):
    def _packet(self, root: Path) -> Path:
        packet_dir = root / "packet"
        packet_dir.mkdir()
        packet = {
            "kind": "bloxbench-pairwise-human-review-v3",
            "fixture": {"id": "pilot.example"},
            "labels": {"A": {"artifacts": []}, "B": {"artifacts": []}},
            "automated_boundary": {
                "quality_scored": False,
                "allowed_human_labels": ["A better", "B better", "tie", "both bad"],
            },
            "human_decision": None,
        }
        (packet_dir / "packet.json").write_text(json.dumps(packet), encoding="utf-8")
        (packet_dir / "review_form.json").write_text(
            json.dumps(
                {
                    "schema": "bloxbench-human-review-form-v1",
                    "packet_kind": packet["kind"],
                    "fixture_id": "pilot.example",
                    "allowed_labels": packet["automated_boundary"]["allowed_human_labels"],
                    "label": None,
                    "notes": None,
                    "reviewer": None,
                }
            ),
            encoding="utf-8",
        )
        return packet_dir

    def test_invalid_label_is_rejected_without_mutating_packet(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            packet_dir = self._packet(Path(raw))
            form_path = packet_dir / "review_form.json"
            form = json.loads(form_path.read_text())
            form["label"] = "A wins"
            form_path.write_text(json.dumps(form), encoding="utf-8")
            before = (packet_dir / "packet.json").read_text()
            with self.assertRaisesRegex(ValueError, "allowed human label"):
                ingest_human_review(packet_dir)
            self.assertEqual((packet_dir / "packet.json").read_text(), before)

    def test_valid_label_is_persisted_as_a_human_decision(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            packet_dir = self._packet(Path(raw))
            form_path = packet_dir / "review_form.json"
            form = json.loads(form_path.read_text())
            form.update({"label": "B better", "notes": "B has the clearer focal hierarchy.", "reviewer": "r1"})
            form_path.write_text(json.dumps(form), encoding="utf-8")
            output = ingest_human_review(packet_dir)
            packet = json.loads(output.read_text())
            self.assertEqual(packet["human_decision"]["label"], "B better")
            self.assertEqual(packet["human_decision"]["reviewer"], "r1")
            self.assertTrue(packet["human_decision"]["notes_sha256"])
            self.assertFalse(packet["automated_boundary"]["quality_scored"])
            self.assertTrue((packet_dir / "human_decision.json").is_file())

    def test_decision_cannot_be_overwritten_implicitly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            packet_dir = self._packet(Path(raw))
            form_path = packet_dir / "review_form.json"
            form = json.loads(form_path.read_text())
            form["label"] = "tie"
            form_path.write_text(json.dumps(form), encoding="utf-8")
            ingest_human_review(packet_dir)
            with self.assertRaisesRegex(ValueError, "already recorded"):
                ingest_human_review(packet_dir)


if __name__ == "__main__":
    unittest.main()
