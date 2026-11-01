"""
Servicio de inferencia: toma texto libre, ejecuta el predictor,
y devuelve resultados estructurados compatibles con el frontend.
"""

from __future__ import annotations

import re
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ml.predictor import SentenceResult
from models.schemas import ACTION_LABELS


def run_inference(text: str) -> dict:
    """
    Ejecuta inferencia sobre texto libre.

    Returns:
        dict con keys: sentences, grouped_items, spans
    """
    from ml.predictor import get_predictor

    predictor = get_predictor()
    results = predictor.predict(text)

    # Construir grouped_items
    grouped_items = {label: [] for label in ACTION_LABELS}
    for result in results:
        for label in result.labels:
            if label in grouped_items:
                if result.sentence not in grouped_items[label]:
                    grouped_items[label].append(result.sentence)

    # Construir spans buscando cada frase en el texto original
    spans = _build_spans_from_results(text, results)

    # Serializar sentences
    sentence_dicts = [r.to_dict() for r in results]

    return {
        "sentences": sentence_dicts,
        "grouped_items": grouped_items,
        "spans": spans,
    }


def _build_spans_from_results(
    text: str, results: List[SentenceResult]
) -> List[dict]:
    """
    Busca cada frase predicha en el texto original para generar spans
    con posiciones start/end, igual que los del dataset viewer.
    """
    spans = []
    used_positions = set()

    for result in results:
        sentence = result.sentence
        # Buscar la frase en el texto original
        positions = _find_sentence_in_text(text, sentence, used_positions)

        if positions:
            start, end = positions
            used_positions.add((start, end))

            for label in result.labels:
                confidence = result.confidences.get(label, 0.0)
                spans.append({
                    "start": start,
                    "end": end,
                    "label": label,
                    "text": text[start:end],
                    "confidence": confidence,
                    "raw_labels": result.labels,
                })

    # Ordenar: por posición, luego confianza ascendente.
    # El último span para cada posición "gana" el color del highlight,
    # así que ponemos el de mayor confianza al final.
    spans.sort(key=lambda x: (x["start"], x["end"], x["confidence"]))
    return spans


def _find_sentence_in_text(
    text: str,
    sentence: str,
    used: set,
) -> Tuple[int, int] | None:
    """Locate complete evidence, allowing only whitespace normalization."""
    words = sentence.split()
    if not words:
        return None
    pattern = r"\s+".join(re.escape(word) for word in words)
    for match in re.finditer(pattern, text):
        position = (match.start(), match.end())
        if position not in used:
            return position

    return None
