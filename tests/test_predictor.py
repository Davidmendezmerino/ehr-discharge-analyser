"""Threshold-boundary and missing-artifact regression cases."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app/api"))
from ml.predictor import Predictor


class FixedClassifier:
    def __init__(self, probability):
        self.probability = probability

    def predict_proba(self, values):
        return np.tile([1 - self.probability, self.probability], (len(values), 1))


def predictor_with_score(score):
    predictor = Predictor.__new__(Predictor)
    predictor.encoder = SimpleNamespace(encode=lambda sentences, **kwargs: np.zeros((len(sentences), 2)))
    predictor.mlb = SimpleNamespace(classes_=["Appointment"])
    predictor.classifiers = {"Appointment": FixedClassifier(score)}
    predictor.thresholds = {"Appointment": 0.35}
    return predictor


class PredictorTests(unittest.TestCase):
    def test_rounding_cannot_promote_a_score_below_the_threshold(self):
        result = predictor_with_score(0.3496).predict("Follow up with cardiology in one week.")
        self.assertEqual(result, [])

    def test_score_at_the_threshold_is_included(self):
        result = predictor_with_score(0.35).predict("Follow up with cardiology in one week.")
        self.assertEqual(result[0].labels, ["Appointment"])
        self.assertEqual(result[0].confidences, {"Appointment": 0.35})

    def test_missing_model_points_to_the_available_download_script(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("ml.predictor.ARTIFACTS_DIR", Path(folder)):
                with self.assertRaisesRegex(FileNotFoundError, "scripts/download_artifacts.py"):
                    Predictor()


if __name__ == "__main__":
    unittest.main()
