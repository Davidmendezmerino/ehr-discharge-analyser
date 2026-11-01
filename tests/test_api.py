"""HTTP contract checks that do not require loading the encoder."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app/api"))
from main import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_health_does_not_require_loading_the_model(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_unused_routes_do_not_claim_to_extract_or_redact(self):
        for route in ("/clip/extract", "/deid/redact"):
            with self.subTest(route=route):
                response = self.client.post(route, json={"text": "Synthetic test text."})
                self.assertEqual(response.status_code, 501)
                self.assertIn("not implemented", response.json()["detail"])

    def test_oversized_text_is_rejected_before_inference(self):
        with patch("main.run_inference") as inference:
            response = self.client.post("/clip/infer", json={"text": "x" * 50_001})
            self.assertEqual(response.status_code, 413)
            inference.assert_not_called()

    def test_missing_artifacts_return_service_unavailable(self):
        with patch("main.run_inference", side_effect=FileNotFoundError("Model artifacts are missing.")):
            response = self.client.post("/clip/infer", json={"text": "Synthetic test text."})
            self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
