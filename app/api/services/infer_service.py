"""
Servicio de inferencia: toma texto libre, ejecuta el predictor,
y devuelve resultados estructurados compatibles con el frontend.
"""

import re
from typing import Dict, List, Tuple

from ml.predictor import get_predictor, SentenceResult
from models.schemas import ACTION_LABELS


def run_inference(text: str) -> dict:
    """
    Ejecuta inferencia sobre texto libre.

    Returns:
        dict con keys: sentences, grouped_items, spans
    """
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
    """Busca una frase en el texto, intentando coincidencia exacta y luego fuzzy."""
    # Intento 1: búsqueda exacta
    idx = text.find(sentence)
    if idx >= 0:
        pos = (idx, idx + len(sentence))
        if pos not in used:
            return pos

    # Intento 2: buscar con espacios normalizados
    pattern = re.escape(sentence)
    pattern = pattern.replace(r"\ ", r"\s+")
    match = re.search(pattern, text)
    if match:
        pos = (match.start(), match.end())
        if pos not in used:
            return pos

    # Intento 3: buscar las primeras N palabras como anclaje
    words = sentence.split()
    if len(words) >= 3:
        anchor = r"\s+".join(re.escape(w) for w in words[:4])
        match = re.search(anchor, text)
        if match:
            # Extender hasta el final de la línea o siguiente punto
            end_idx = match.start() + len(sentence)
            end_idx = min(end_idx, len(text))
            pos = (match.start(), end_idx)
            if pos not in used:
                return pos

    return None
