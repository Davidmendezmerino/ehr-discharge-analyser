# Source and packaging

Application copied from the author's public [EHR Discharge Analyser Space](https://huggingface.co/spaces/Dwagga/ehr-discharge-analyser/tree/c91683b4d68be5c3d80695b23cc9b6d33081bbe8), revision `c91683b4d68be5c3d80695b23cc9b6d33081bbe8`, retrieved 1 November 2026.

The application starts from that published revision. The GitHub edition adds project documentation, a screenshot, an artifact-download helper and regression checks. It does not change the public Space or retrain a model.

Reliability fixes in this repository:

- Locate every occurrence of a classified sentence, preserving source offsets across line wrapping; do not create evidence from a matching prefix alone.
- Apply the existing label thresholds to full-precision scores before rounding the reported confidences.
- Return HTTP 501 for the two unused extraction/redaction placeholders rather than reporting success.
- Correct the missing-artifact instructions and recover UTF-8 comments in the predictor.
- Use Python for the container readiness check, retain installed runtime dependencies, clean up both services on exit and provide commands for the component Dockerfiles.

The original Hugging Face demo remains at the linked source revision. These code fixes do not establish model accuracy, clinical validation or FHIR conformance.

The encoder's model card identifies [pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb](https://huggingface.co/pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb) as its base. Its [original model card](https://huggingface.co/spaces/Dwagga/ehr-discharge-analyser/blob/c91683b4d68be5c3d80695b23cc9b6d33081bbe8/app/api/ml/artifacts/finetuned-biobert/README.md) records a fine-tuned sentence transformer with 768-dimensional embeddings and 50,000 training pairs. This is not a count of patients or unique documents, and it is not an independent evaluation.

The auto-generated model card and training text examples are not republished here. The runtime downloader includes only the encoder/tokenizer configuration, weights, classifier, label mapping and thresholds. Artifact files remain hosted at the pinned public Space; their expected sizes and hashes are in `artifacts.manifest.json`.

The original Space metadata declares `license: apache-2.0`. That metadata is preserved as provenance, without assigning new terms to third-party pretrained models. The screenshot is from the existing application.
