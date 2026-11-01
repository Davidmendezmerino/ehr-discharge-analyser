# Runtime model files

From the repository root, run `python scripts/download_artifacts.py` before starting the application. It downloads the encoder, tokenizer, classifiers, label mapping and thresholds from the pinned public Hugging Face revision and verifies them against `artifacts.manifest.json`.

The runtime files are ignored by Git. The source model card and provenance are linked from the root `SOURCE.md`.
