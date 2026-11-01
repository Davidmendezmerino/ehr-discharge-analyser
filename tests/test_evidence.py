"""Regression cases for exact source evidence, without loading model weights."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app/api"))
from services.infer_service import _build_spans_from_results, _find_sentence_in_text


class EvidenceTests(unittest.TestCase):
    def test_repeated_sentences_map_to_distinct_occurrences(self):
        sentence = "Follow up with cardiology in one week."
        text = sentence + "\n" + sentence
        result = SimpleNamespace(sentence=sentence, labels=["Appointment"], confidences={"Appointment": 0.9})
        spans = _build_spans_from_results(text, [result, result])
        self.assertEqual([(span["start"], span["end"]) for span in spans],
                         [(0, len(sentence)), (len(sentence) + 1, len(text))])
        self.assertTrue(all(span["text"] == sentence for span in spans))

    def test_wrapped_whitespace_preserves_original_offsets(self):
        text = "Follow  up with\ncardiology in one week."
        sentence = "Follow up with cardiology in one week."
        self.assertEqual(_find_sentence_in_text(text, sentence, set()), (0, len(text)))

    def test_document_order_wins_over_exact_whitespace(self):
        first = "Follow  up with\ncardiology in one week."
        sentence = "Follow up with cardiology in one week."
        text = first + "\n" + sentence
        self.assertEqual(_find_sentence_in_text(text, sentence, set()), (0, len(first)))
        self.assertEqual(_find_sentence_in_text(text, sentence, {(0, len(first))}),
                         (len(first) + 1, len(text)))

    def test_matching_prefix_cannot_fabricate_evidence(self):
        text = "Follow up with cardiology after the appointment."
        prediction = "Follow up with cardiology tomorrow for imaging."
        self.assertIsNone(_find_sentence_in_text(text, prediction, set()))

    def test_multilabel_results_share_the_verified_evidence(self):
        text = "Schedule imaging at the follow-up appointment."
        result = SimpleNamespace(sentence=text, labels=["Appointment", "Imaging"],
                                 confidences={"Appointment": 0.8, "Imaging": 0.9})
        spans = _build_spans_from_results(text, [result])
        self.assertEqual({span["label"] for span in spans}, {"Appointment", "Imaging"})
        self.assertTrue(all(span["start"] == 0 and span["end"] == len(text) for span in spans))


if __name__ == "__main__":
    unittest.main()
