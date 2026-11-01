"""
Módulo de inferencia: carga el modelo entrenado y predice labels
para frases nuevas.

Uso:
    from ml.predictor import get_predictor
    predictor = get_predictor()
    results = predictor.predict("Patient should follow up in 2 weeks.")
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import numpy as np

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
DEFAULT_THRESHOLD = 0.35


class SentenceResult:
    """Resultado de predicción para una frase."""

    def __init__(
        self,
        sentence: str,
        labels: List[str],
        confidences: Dict[str, float],
    ):
        self.sentence = sentence
        self.labels = labels
        self.confidences = confidences

    def to_dict(self) -> dict:
        return {
            "sentence": self.sentence,
            "labels": self.labels,
            "confidences": self.confidences,
        }


class Predictor:
    """Carga el encoder + clasificadores y expone predict()."""

    def __init__(self):
        pipeline_path = ARTIFACTS_DIR / "pipeline.joblib"
        mlb_path = ARTIFACTS_DIR / "mlb.joblib"
        thresholds_path = ARTIFACTS_DIR / "thresholds.json"

        if not pipeline_path.exists() or not mlb_path.exists():
            raise FileNotFoundError(
                f"Model artifacts are missing from {ARTIFACTS_DIR}. "
                "From the repository root, run: python scripts/download_artifacts.py"
            )

        from sentence_transformers import SentenceTransformer

        artifacts = joblib.load(pipeline_path)
        model_name = artifacts["model_name"]
        self.classifiers = artifacts["classifiers"]
        self.mlb = joblib.load(mlb_path)

        # Cargar el encoder de sentence embeddings
        # Si model_name es una ruta local (e.g. 'ml/artifacts/finetuned-biobert'),
        # resolver como path absoluto; si no, tratar como nombre HuggingFace.
        model_path = model_name
        if not model_name.startswith("/") and "/" in model_name:
            # Ruta relativa → resolver desde /app/ (Docker) o desde el proyecto
            candidates = [
                Path("/app") / model_name,               # Docker
                Path(__file__).resolve().parents[1] / model_name,  # Local (desde ml/)
                ARTIFACTS_DIR / "finetuned-biobert",       # Fallback directo
            ]
            for candidate in candidates:
                if candidate.exists():
                    model_path = str(candidate)
                    break

        print(f"Cargando SentenceTransformer: {model_path}...")
        self.encoder = SentenceTransformer(model_path)
        print("Encoder cargado.")

        # Cargar thresholds por label (si existen)
        if thresholds_path.exists():
            with open(thresholds_path, "r") as f:
                self.thresholds = json.load(f)
            print(f"Thresholds por label cargados: {self.thresholds}")
        else:
            self.thresholds = {}
            print(f"thresholds.json no encontrado, usando threshold global: {DEFAULT_THRESHOLD}")

    # Patrones de frases no-accionables (metadata, narrativa, headers)
    _NON_ACTIONABLE = re.compile(
        r'^\s*('
        # Metadata / demografía del paciente
        r'Patient\s+(Name|ID|DOB|Date of Birth|Age|Sex|Gender|MRN|Account)'
        r'|Date of (Birth|Admission|Discharge|Service)'
        r'|Admission Date|Discharge Date|Service Date'
        r'|MRN\s*[:#]|Account\s*[:#]'
        r'|Attending\s*[:#]|Dictated\s+[Bb]y|Signed\s+[Bb]y'
        r'|Completed\s+by'
        # Headers de sección
        r'|DISCHARGE SUMMARY\s*[:#]?$'
        r'|DISCHARGE DIAGNOSIS|DISCHARGE CONDITION|DISCHARGE DISPOSITION'
        r'|ADMITTING DIAGNOSIS|PRINCIPAL DIAGNOSIS'
        r'|HISTORY OF PRESENT ILLNESS|HOSPITAL COURSE'
        r'|SOCIAL HISTORY|FAMILY HISTORY|PAST MEDICAL HISTORY'
        r'|ALLERGIES|REVIEW OF SYSTEMS'
        r'|PHYSICAL EXAMINATION|VITAL SIGNS'
        r')',
        re.IGNORECASE
    )

    # Patrones de narrativa/historia (frases que describen lo que pasó, no instrucciones)
    _NARRATIVE_PATTERNS = re.compile(
        r'('
        r'evaluated the patient'
        r'|was (admitted|discharged|consulted|evaluated|assessed|seen|noted|observed|started|placed|transferred)'
        r'|the patient was'
        r'|patient (was|is|has been|had|presented|tolerated|reported|denied|underwent)'
        r'|during (the |this )?(admission|hospitalization|stay|visit)'
        r'|on (arrival|presentation|admission)'
        r'|at the time of (discharge|admission)'
        r'|hospital course'
        r')',
        re.IGNORECASE
    )

    # Instruction keywords that override narrative filter
    _INSTRUCTION_WORDS = re.compile(
        r'\b('
        r'should|must|please|need to|needs to'
        r'|follow[\s-]?up|schedule|obtain|check|start|stop|begin'
        r'|continue|discontinue|resume|hold'
        r'|take|avoid|return|call|monitor|repeat|refer|arrange'
        r'|increase|decrease|titrate|taper|wean|adjust'
        r'|do not|don\'t|refrain'
        r'|make (an |a )?appointment'
        r'|come back|go to|see (your|a|the)|visit'
        r'|contact|notify|inform|report'
        r')\b',
        re.IGNORECASE
    )

    # Minimum thresholds for sentence quality
    _MIN_SENTENCE_CHARS = 10
    _MIN_SENTENCE_WORDS = 1

    def _is_actionable(self, sentence: str) -> bool:
        """
        Filtra frases no-accionables: metadata, headers, narrativa, fragments.
        Devuelve True si la frase podría contener instrucciones accionables.
        """
        s = sentence.strip()

        # Too short to be a meaningful instruction
        if len(s) < self._MIN_SENTENCE_CHARS:
            return False

        # Too few words (fragments like "pneumonia.", "PREDNISONE.")
        word_count = len(s.split())
        if word_count < self._MIN_SENTENCE_WORDS:
            return False

        # Metadata / demographics / headers
        if self._NON_ACTIONABLE.search(s):
            return False

        # Narrative: only filter if NO instruction keywords present
        has_instruction = self._INSTRUCTION_WORDS.search(s)
        if not has_instruction and self._NARRATIVE_PATTERNS.search(s):
            return False

        return True

    # ── Section-aware parsing ──────────────────────────────────────
    # Sections where content is actionable (discharge instructions)
    _ACTIONABLE_SECTIONS = {
        "discharge instructions",
        "discharge plan",
        "discharge medications",
        "medications on discharge",
        "medications at discharge",
        "discharge meds",
        "follow-up",
        "follow up",
        "followup",
        "follow-up instructions",
        "plan",
        "disposition",
        "discharge orders",
        "instructions",
        "patient instructions",
        "aftercare instructions",
        "discharge condition and instructions",
    }

    # Sections that are definitely NOT actionable
    _NARRATIVE_SECTIONS = {
        "history of present illness",
        "hospital course",
        "brief hospital course",
        "past medical history",
        "social history",
        "family history",
        "review of systems",
        "physical examination",
        "vital signs",
        "laboratory data",
        "pertinent results",
        "imaging",
        "radiology",
        "micro",
        "chief complaint",
        "admitting diagnosis",
        "discharge diagnosis",
        "discharge condition",
        "allergies",
        "medications on admission",
        "admission medications",
        "assessment and plan",
        "assessment",
        "major surgical or invasive procedure",
        "service",
        "attending",
    }

    # Single-word tokens that look like headers but are actually
    # metadata fields inside content (e.g. "Provider: Dr. Smith").
    # These must NOT create section boundaries.
    _FALSE_HEADER_TOKENS = {
        "provider", "date", "time", "date/time", "phone", "fax",
        "location", "address", "building", "campus", "floor",
        "room", "suite", "clinic", "department", "contact",
        "when", "with", "where", "best parking", "facility",
        "name", "completed by", "dictated by", "signed by",
        "comments", "note", "impression", "conclusions",
        "findings", "indication", "technique", "comparison",
        "history", "reason", "results", "interpretation",
        "lcx", "lad", "rca",  # coronary artery abbreviations
        "gram stain", "respiratory culture", "nuclear imaging",
        "cardiac catheterization", "final diagnosis",
    }

    # Regex to detect section headers
    _SECTION_HEADER = re.compile(
        r'^[\s]*'              # optional leading whitespace
        r'([A-Z][A-Za-z /\-&]+?)'  # section name (starts with capital)
        r'\s*[:]\s*$'          # ends with colon
        r'|'
        r'^[\s]*'
        r'([A-Z][A-Z /\-&]{3,})'  # ALL-CAPS header (at least 4 chars)
        r'\s*[:\.]?\s*$',       # optional colon/period at end
        re.MULTILINE
    )

    @classmethod
    def _extract_actionable_text(cls, text: str) -> str | None:
        """
        Parse the document into sections and return ONLY the text from
        actionable sections (Discharge Instructions, Medications, etc.).
        Unknown sub-headers inherit their parent section's classification.

        Returns None if no clear section structure is detected (fallback).
        """
        lines = text.split('\n')

        # First pass: detect all section boundaries
        # Each entry: (start_line, section_name, inline_start_text_or_None)
        sections = []
        for i, line in enumerate(lines):
            stripped = line.strip().rstrip(':.').strip()
            if not stripped:
                continue

            # Check if this line looks like a section header
            is_header = False
            header_name = ""
            inline_start = None  # text after colon on same line

            # Pattern 1: "Section Name:" (title case with colon, nothing after)
            if line.strip().endswith(':') and len(stripped.split()) <= 8:
                words = stripped.split()
                # At least one word starts with capital
                if any(w[0].isupper() for w in words if w):
                    is_header = True
                    header_name = stripped.lower()

            # Pattern 2: ALL CAPS line (at least 3 chars, mostly alpha)
            if not is_header and len(stripped) >= 3:
                alpha_chars = sum(1 for c in stripped if c.isalpha())
                if alpha_chars > 0 and stripped.upper() == stripped and alpha_chars / len(stripped) > 0.6:
                    is_header = True
                    header_name = stripped.lower()

            # Pattern 3: Inline header — "SECTION NAME:  Content starts here"
            # Common in MIMIC-III: header and content on the same line
            if not is_header and ':' in line:
                colon_pos = line.index(':')
                before = line[:colon_pos].strip()
                after = line[colon_pos + 1:].strip()
                # Header part must be short (≤8 words), mostly uppercase or title case
                if before and after and len(before.split()) <= 8:
                    before_clean = before.rstrip(':.').strip()
                    alpha_count = sum(1 for c in before_clean if c.isalpha())
                    is_upper = before_clean.upper() == before_clean and alpha_count >= 3
                    is_title = any(w[0].isupper() for w in before_clean.split() if w)
                    if (is_upper or is_title) and alpha_count / max(len(before_clean), 1) > 0.6:
                        is_header = True
                        header_name = before_clean.lower()
                        inline_start = after

            if is_header:
                # Normalize header name
                header_name = re.sub(r'\s+', ' ', header_name).strip()
                # Skip false-positive headers (metadata tokens inside content)
                if header_name in cls._FALSE_HEADER_TOKENS:
                    continue
                sections.append((i, header_name, inline_start))

        # Need at least 2 sections to consider it a structured document
        if len(sections) < 2:
            return None

        # Check if we have at least one actionable section
        has_actionable = any(
            any(act in name for act in cls._ACTIONABLE_SECTIONS)
            for _, name, _ in sections
        )
        if not has_actionable:
            return None

        # Second pass: extract text only from actionable sections
        actionable_text_parts = []

        for idx, (start_line, name, inline_start) in enumerate(sections):
            # Determine end of this section
            if idx + 1 < len(sections):
                end_line = sections[idx + 1][0]
            else:
                end_line = len(lines)

            # Check if this section is actionable
            is_actionable = any(act in name for act in cls._ACTIONABLE_SECTIONS)

            if is_actionable:
                parts = []
                # If header had inline content, include it
                if inline_start:
                    parts.append(inline_start)
                # Collect remaining lines in this section (skip header line)
                section_lines = lines[start_line + 1:end_line]
                section_text = '\n'.join(section_lines).strip()
                if section_text:
                    parts.append(section_text)
                if parts:
                    actionable_text_parts.append('\n'.join(parts))

        if not actionable_text_parts:
            return None

        return '\n\n'.join(actionable_text_parts)

    def predict(self, text: str) -> List[SentenceResult]:
        """
        Divide el texto en frases y clasifica cada una.
        Devuelve solo las frases que tienen al menos un label positivo.

        If the document has clear section structure, only sentences from
        actionable sections (Discharge Instructions, Medications, etc.)
        are classified. Otherwise, falls back to full-text classification.
        """
        # Try section-aware parsing first
        actionable_text = self._extract_actionable_text(text)
        classify_text = actionable_text if actionable_text is not None else text

        sentences = self._split_sentences(classify_text)
        if not sentences:
            return []

        # Filtrar frases no-accionables antes de clasificar
        sentences = [s for s in sentences if self._is_actionable(s)]
        if not sentences:
            return []

        # Generar embeddings
        X = self.encoder.encode(sentences, normalize_embeddings=True)

        # Obtener probabilidades de cada clasificador
        proba_matrix = np.zeros((len(sentences), len(self.mlb.classes_)))
        for j, label in enumerate(self.mlb.classes_):
            clf = self.classifiers[label]
            proba_matrix[:, j] = clf.predict_proba(X)[:, 1]

        # Labels más específicos que Patient Instructions
        SPECIFIC_LABELS = {"Appointment", "Medication", "Lab", "Procedure", "Imaging"}

        results = []
        for i, sentence in enumerate(sentences):
            proba_row = proba_matrix[i]

            active_labels = []
            confidences = {}

            for j, label in enumerate(self.mlb.classes_):
                raw_confidence = float(proba_row[j])
                # Usar threshold específico del label, o el global
                threshold = self.thresholds.get(label, DEFAULT_THRESHOLD)
                if raw_confidence >= threshold:
                    active_labels.append(label)
                    confidences[label] = round(raw_confidence, 3)

            # Post-procesamiento: mutual exclusion para Patient Instructions
            # Si PI coexiste con un label más específico, eliminar PI
            if "Patient Instructions" in active_labels and len(active_labels) > 1:
                has_specific = any(
                    label in SPECIFIC_LABELS
                    for label in active_labels
                )
                if has_specific:
                    active_labels.remove("Patient Instructions")
                    del confidences["Patient Instructions"]

            # Same logic for Other: if it coexists with a specific label, drop it
            if "Other" in active_labels and len(active_labels) > 1:
                has_specific = any(
                    label in SPECIFIC_LABELS
                    for label in active_labels
                )
                if has_specific:
                    active_labels.remove("Other")
                    del confidences["Other"]

            if active_labels:
                results.append(SentenceResult(
                    sentence=sentence,
                    labels=active_labels,
                    confidences=confidences,
                ))

        return results

    # Abreviaturas que NO deben cortar frases
    _ABBREVS = re.compile(
        r'\b('
        # Títulos
        r'Dr|Mr|Mrs|Ms|Prof|Sr|Jr|Rev'
        # Médicas
        r'|Pt|Dx|Rx|Tx|Hx|Sx|Bx|Fx|Cx|Px|Mx'
        r'|Drs|Surg|Med|Pharm|Rehab|Psych'
        # Unidades / medidas
        r'|mg|ml|kg|lb|oz|hr|min|sec|vol|amt|temp|approx|avg|est|max|min'
        # Localizaciones / direcciones
        r'|St|Ave|Blvd|Rd|Ct|Apt|Dept|Bldg|Rm|Fl'
        # Generales
        r'|vs|etc|no|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec'
        r'|Inc|Corp|Ltd|Co|Gen|Assoc|Univ|Hosp'
        r'|i\.e|e\.g|a\.m|p\.m'
        r')\.',
        re.IGNORECASE
    )
    _PLACEHOLDER = '\x00'  # carácter temporal para proteger abreviaturas

    # Prefijos de sección que aparecen inline (ej: "Discharge Instructions: Take...")
    _INLINE_PREFIXES = re.compile(
        r'^\s*('
        r'Discharge\s+(Instructions|Summary|Plan|Orders)'
        r'|Discharge\s+Disposition'
        r'|Instructions'
        r'|Plan'
        r'|Discharge\s+Plan'
        r'|Discharge\s+Medications'
        r')\s*:\s*',
        re.IGNORECASE
    )

    @classmethod
    def _split_sentences(cls, text: str) -> List[str]:
        """
        Divide texto en frases protegiendo abreviaturas comunes.
        1. Join wrapped lines into paragraphs (blank line = paragraph break)
        2. Split paragraphs by sentence-ending punctuation
        3. Filter short fragments and section headers
        4. Strip inline section prefixes
        """
        # Proteger abreviaturas: "Dr." → "Dr\x00"
        protected = cls._ABBREVS.sub(lambda m: m.group(1) + cls._PLACEHOLDER, text)

        # ── Step 1: Join wrapped lines into paragraphs ──
        # In clinical documents (MIMIC-III), text wraps at ~80 chars.
        # A line that does NOT end with sentence-ending punctuation (.!?)
        # MAY be a continuation of the previous line (hard-wrap) OR
        # a standalone list item (e.g., medication without trailing period).
        #
        # Heuristic: only join to previous line if the previous line is long
        # (>60 chars), which indicates a hard-wrap break. Short lines are
        # likely standalone items and should remain separate.
        # Blank lines always mark paragraph boundaries.
        raw_lines = protected.split("\n")
        paragraphs = []
        current_para = []

        for raw_line in raw_lines:
            stripped = raw_line.strip()

            if not stripped:
                # Blank line → end current paragraph
                if current_para:
                    paragraphs.append(" ".join(current_para))
                    current_para = []
                continue

            # Decide whether to join to current paragraph or start a new one
            if current_para:
                prev_line = current_para[-1]
                # Only join if previous line was long (hard-wrap) and didn't
                # end with punctuation
                if len(prev_line) > 60 and prev_line[-1] not in '.!?':
                    current_para.append(stripped)
                else:
                    # Previous line was short or ended with punctuation:
                    # treat it as a complete item
                    paragraphs.append(" ".join(current_para))
                    current_para = [stripped]
            else:
                current_para.append(stripped)

            # If line ends with sentence-ending punctuation, close paragraph
            if stripped[-1] in '.!?':
                paragraphs.append(" ".join(current_para))
                current_para = []

        # Flush remaining
        if current_para:
            paragraphs.append(" ".join(current_para))

        # ── Step 2: Split paragraphs into sentences ──
        sentences = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Split by sentence-ending punctuation followed by space + capital
            parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', para)
            for part in parts:
                # Restaurar abreviaturas: "Dr\x00" → "Dr."
                part = part.replace(cls._PLACEHOLDER, '.').strip()
                if len(part) >= 5 and not cls._is_section_header(part):
                    # Strip inline section prefixes
                    part = cls._INLINE_PREFIXES.sub('', part).strip()
                    if len(part) >= 5:
                        sentences.append(part)

        return sentences

    @staticmethod
    def _is_section_header(text: str) -> bool:
        """Detecta encabezados de sección como 'Discharge Instructions:'."""
        stripped = text.rstrip('.')
        # Encabezado: termina en ":" y tiene pocas palabras
        if stripped.endswith(':') and len(stripped.split()) <= 6:
            return True
        return False


# --- Singleton ---
_predictor: Optional[Predictor] = None


def get_predictor() -> Predictor:
    """Devuelve instancia singleton del predictor (lazy loading)."""
    global _predictor
    if _predictor is None:
        _predictor = Predictor()
    return _predictor
