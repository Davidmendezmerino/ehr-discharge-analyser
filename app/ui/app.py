import html
import json
import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ── Label config ───────────────────────────────────────────────────
LABEL_COLORS = {
    "Appointment":           "#dbeafe",
    "Medication":            "#dcfce7",
    "Lab":                   "#fef3c7",
    "Patient Instructions":  "#fecaca",
    "Procedure":             "#ede9fe",
    "Imaging":               "#cffafe",
    "Other":                 "#e5e7eb",
}

LABEL_ICONS = {
    "Appointment":           "📅",
    "Medication":            "💊",
    "Lab":                   "🔬",
    "Patient Instructions":  "📋",
    "Procedure":             "🏥",
    "Imaging":               "📷",
    "Other":                 "📝",
}

# ── Example discharge summaries for quick demo ─────────────────────
EXAMPLE_TEXTS = {
    "Heart Failure": """\
DISCHARGE SUMMARY

Patient: 72-year-old male
Admission Date: 2024-01-15
Discharge Date: 2024-01-19
Attending: Dr. Sarah Chen, Cardiology

Chief Complaint: Progressive dyspnea and lower extremity edema over 3 days.

Brief Hospital Course:
The patient presented with acute decompensated heart failure (EF 30%, down from 45% six months ago). He was admitted to the cardiac step-down unit and started on IV furosemide with good diuretic response. Daily weights showed a 4.2 kg fluid loss over hospitalization. BNP trended down from 1,850 to 620 pg/mL. Telemetry was unremarkable. He was transitioned to oral diuretics on hospital day 3 and remained stable with oxygen saturations above 94% on room air.

Past Medical History: Hypertension, Type 2 Diabetes (A1c 7.4%), Hyperlipidemia, Atrial fibrillation (rate-controlled), CKD Stage IIIA (baseline Cr 1.4).

Discharge Instructions:
Start Furosemide 40 mg PO BID, to be titrated based on daily weight and renal function. Check comprehensive metabolic panel (BMP) in 5-7 days to monitor renal function and potassium levels. Titrate Carvedilol dosage as tolerated during next visit, goal dose 25 mg BID. Schedule follow-up with Cardiology within 2 weeks. Daily weights and call if weight increases by more than 3 lbs in 24 hours. Maintain a low-sodium diet (less than 2g/day) and restrict fluid intake to 2 liters per day. Continue Apixaban 5 mg BID for atrial fibrillation. Return to ED for worsening shortness of breath, chest pain, or weight gain greater than 5 lbs in one week.""",

    "Pneumonia": """\
DISCHARGE SUMMARY

Patient: 55-year-old female
Admission Date: 2024-02-08
Discharge Date: 2024-02-11
Attending: Dr. Michael Torres, Internal Medicine

Chief Complaint: Fever (39.1°C), productive cough with yellow sputum, and pleuritic chest pain for 4 days.

Brief Hospital Course:
The patient was admitted with community-acquired pneumonia. Chest X-ray revealed a right lower lobe consolidation. Blood cultures were drawn prior to antibiotic initiation and remained negative at 48 hours. She was started on IV ceftriaxone and azithromycin with clinical improvement noted by day 2. Oxygen requirements decreased from 3L nasal cannula to room air. WBC normalized from 15.2 to 8.7. She remained afebrile for over 24 hours prior to discharge. She was transitioned to oral antibiotics.

Past Medical History: Asthma (mild intermittent), GERD, former smoker (quit 8 years ago, 15 pack-year history).

Social History: Works as a schoolteacher, lives with spouse and two children. No alcohol or illicit drug use.

Discharge Instructions:
Continue amoxicillin-clavulanate 875/125 mg by mouth twice daily for 5 additional days (last day: February 16). Start Prednisone 40 mg daily for 5 days for post-infectious bronchospasm. Take albuterol 2 puffs every 6 hours as needed for wheezing. Follow up with your primary care physician in 7-10 days for clinical reassessment and to review repeat inflammatory markers. Obtain a repeat chest X-ray in 6 weeks to confirm radiographic resolution and exclude underlying pathology. Return to the ED if you develop worsening shortness of breath, chest pain, hemoptysis, or fever above 38.5°C. Increase fluid intake and rest for the first week. You may return to work when afebrile for 48 hours without antipyretics.""",

    "Post-Surgical": """\
DISCHARGE SUMMARY

Patient: 58-year-old female
Admission Date: 2024-03-01
Discharge Date: 2024-03-03
Attending: Dr. James Park, General Surgery

Chief Complaint: Right upper quadrant abdominal pain, nausea, and vomiting after fatty meal.

Brief Hospital Course:
The patient presented with acute cholecystitis confirmed by RUQ ultrasound showing gallbladder wall thickening (5mm), pericholecystic fluid, and a 1.2 cm impacted stone in the gallbladder neck. Hepatobiliary surgery was consulted and she underwent laparoscopic cholecystectomy on hospital day 1 without complications. Operative time was 45 minutes, EBL minimal. She tolerated a clear liquid diet post-op day 0 and was advanced to a regular diet on post-op day 1. Pain was well controlled with oral analgesics. She was ambulatory and voiding independently prior to discharge.

Past Medical History: Obesity (BMI 34), Prediabetes (A1c 6.2%), Hypothyroidism on Levothyroxine 75 mcg daily.

Discharge Instructions:
Take Acetaminophen 1000 mg by mouth every 8 hours as needed for pain (maximum 3g/day). Wound check in 1 week with General Surgery to ensure all four port sites are healing properly. No heavy lifting over 10 lbs for 4 weeks. No driving while taking opioid pain medications. Follow up with General Surgery in 2 weeks for post-operative evaluation. Resume regular diet as tolerated but avoid high-fat foods for 2-3 weeks. Obtain a CBC and CMP lab work in 3 days to monitor for post-operative complications. Obtain an abdominal ultrasound in 4 weeks to evaluate the surgical site and common bile duct. Keep incision sites clean and dry, may shower after 48 hours but no baths or swimming for 2 weeks. Return to ED for fever above 38.6°C, increasing abdominal pain, persistent nausea or vomiting, jaundice, or wound drainage.""",

}


# ── Custom CSS ─────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Hide Streamlit chrome for demo */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden !important;}
[data-testid="stAppDeployButton"] {display: none;}
.stDeployButton {display: none;}

/* Global overrides */
.main .block-container {
    max-width: 1200px;
    padding-top: 2rem;
}
/* Hide anchor links on headings */
a.header-anchor, .stMarkdown a[href^="#"] svg,
h1 a, h2 a, h3 a, h4 a {
    display: none !important;
}

/* Tab navigation */
button[data-baseweb="tab"] {
    padding: 0.6rem 1.2rem !important;
}
button[data-baseweb="tab"] > * {
    font-size: 1.1rem !important;
    font-weight: 600 !important;
}
button[data-baseweb="tab"]:hover {
    background: rgba(0,0,0,0.04);
    border-radius: 8px 8px 0 0;
}

/* Document text box */
.doc-box {
    white-space: pre-wrap;
    line-height: 1.7;
    font-family: 'Inter', ui-sans-serif, system-ui, sans-serif;
    font-size: 0.9rem;
    padding: 1.25rem 1.5rem;
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 0.75rem;
    background: #fdfdfe;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    max-height: 72vh;
    overflow-y: auto;
}

.side-panel {
    padding: 0.5rem 0.2rem;
}

/* Legend pills */
.legend-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin: 0.5rem 0 1rem 0;
}
.legend-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    border: 1px solid rgba(0,0,0,0.08);
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

/* Highlight spans */
.hl {
    padding: 0.08rem 0.16rem;
    border-radius: 0.3rem;
    border: 1px solid rgba(0,0,0,0.1);
    transition: all 0.15s ease;
}
.hl:hover {
    filter: brightness(0.93);
    box-shadow: 0 1px 4px rgba(0,0,0,0.12);
}
.hl-multi {
    border-style: dashed;
}

.hl-Patient-Instructions { background: #fecaca; }
.hl-Appointment { background: #dbeafe; }
.hl-Medication { background: #dcfce7; }
.hl-Lab { background: #fef3c7; }
.hl-Procedure { background: #ede9fe; }
.hl-Imaging { background: #cffafe; }
.hl-Other { background: #e5e7eb; }

/* Confidence badge */
.confidence-badge {
    display: inline-block;
    padding: 0.1rem 0.4rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;
    background: #e2e8f0;
    margin-left: 0.3rem;
}

/* Summary metrics bar */
.metrics-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    margin: 0.75rem 0;
}
.metric-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.4rem 0.85rem;
    border-radius: 0.5rem;
    font-size: 0.82rem;
    font-weight: 600;
    border: 1px solid rgba(0,0,0,0.06);
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

/* Example buttons row */
.example-label {
    font-size: 0.82rem;
    font-weight: 500;
    color: #64748b;
    margin-bottom: 0.35rem;
}

/* ── Enhanced input section ─────────────────────────── */
.hero-card {
    background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
    border: 1px solid rgba(99, 102, 241, 0.15);
    border-radius: 1rem;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1rem;
}
.hero-card h3 {
    margin: 0 0 0.25rem 0;
    font-size: 1.1rem;
    color: #1e293b;
}
.hero-card p {
    color: #64748b;
    font-size: 0.88rem;
    margin: 0;
    line-height: 1.5;
}

/* Example cards */
.example-cards {
    display: flex;
    gap: 0.75rem;
    margin: 0.75rem 0;
}
.example-card {
    flex: 1;
    background: white;
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 0.75rem;
    padding: 0.85rem 1rem;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: center;
}
.example-card:hover {
    border-color: rgba(99, 102, 241, 0.4);
    box-shadow: 0 2px 8px rgba(99, 102, 241, 0.12);
    transform: translateY(-1px);
}
.example-card .card-icon {
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
}
.example-card .card-title {
    font-weight: 600;
    font-size: 0.85rem;
    color: #1e293b;
}
.example-card .card-desc {
    font-size: 0.72rem;
    color: #94a3b8;
    margin-top: 0.15rem;
}

/* Input hint / word count */
.input-hint {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.75rem;
    color: #94a3b8;
    margin-top: 0.25rem;
    padding: 0 0.25rem;
}

/* Processing stats */
.stats-card {
    background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
    border: 1px solid rgba(34, 197, 94, 0.2);
    border-radius: 0.75rem;
    padding: 1rem 1.25rem;
    margin: 0.5rem 0;
}
.stats-row {
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
}
.stat-item {
    display: flex;
    flex-direction: column;
}
.stat-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: #166534;
}
.stat-label {
    font-size: 0.72rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

/* Pipeline diagram */
.pipeline-step {
    display: flex; align-items: center; gap: 1rem;
    background: white; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 1rem 1.5rem; max-width: 720px; margin: 0 auto;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: transform 0.2s, box-shadow 0.2s;
}
.pipeline-step:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.pipeline-icon { font-size: 2rem; min-width: 48px; text-align: center; }
.pipeline-info { flex: 1; }
.pipeline-title { font-weight: 700; font-size: 0.95rem; color: #1e293b; margin: 0; }
.pipeline-desc { font-size: 0.82rem; color: #64748b; margin: 0.15rem 0 0 0; }
.pipeline-tech { font-size: 0.72rem; color: #94a3b8; font-family: 'Courier New', monospace; margin-top: 0.2rem; }
.pipeline-arrow { font-size: 1.3rem; color: #94a3b8; text-align: center; padding: 0.1rem 0; max-width: 720px; margin: 0 auto; }
</style>
"""

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="EHR Discharge Analyser",
    page_icon="🏥",
    layout="wide",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Header
st.title("🏥 EHR Discharge Summary Analyser")
st.caption("AI-powered extraction of action items from clinical discharge summaries · by David Méndez Merino")

tab1, tab2 = st.tabs(["🔍 Analyser", "🏗️ Architecture"])


# ── Helpers ────────────────────────────────────────────────────────

def get_json(path: str, params: dict | None = None):
    r = requests.get(f"{API_URL}{path}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def post_json(path: str, payload: dict):
    r = requests.post(f"{API_URL}{path}", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()





def css_label_name(label: str) -> str:
    return label.replace(" ", "-")


def render_legend():
    parts = ['<div class="legend-row">']
    for label, color in LABEL_COLORS.items():
        icon = LABEL_ICONS.get(label, "")
        parts.append(
            f'<span class="legend-pill" style="background:{color};">'
            f'{icon} {html.escape(label)}</span>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_metrics_bar(grouped_items: dict):
    """Render a compact metrics summary bar with colored chips."""
    total = sum(len(items) for items in grouped_items.values())
    categories = sum(1 for items in grouped_items.values() if items)

    parts = ['<div class="metrics-bar">']
    parts.append(
        f'<span class="metric-chip" style="background:#f1f5f9;">'
        f'📊 <strong>{total}</strong> action items</span>'
    )
    parts.append(
        f'<span class="metric-chip" style="background:#f1f5f9;">'
        f'🏷️ <strong>{categories}</strong> categories</span>'
    )
    for label, items in grouped_items.items():
        if items:
            color = LABEL_COLORS.get(label, "#e5e7eb")
            icon = LABEL_ICONS.get(label, "")
            parts.append(
                f'<span class="metric-chip" style="background:{color};">'
                f'{icon} {html.escape(label)}: <strong>{len(items)}</strong></span>'
            )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def merge_same_range_spans(spans: list) -> list:
    merged = {}

    for span in spans:
        start = int(span.get("start", 0))
        end = int(span.get("end", 0))
        text = span.get("text", "")
        key = (start, end, text)

        if key not in merged:
            merged[key] = {
                "start": start,
                "end": end,
                "text": text,
                "labels": [],
                "label_confs": {},
                "raw_labels": [],
            }

        label = span.get("label", "Other")
        if label not in merged[key]["labels"]:
            merged[key]["labels"].append(label)
            
        conf = span.get("confidence", 0.0) or 0.0
        merged[key]["label_confs"][label] = max(
            merged[key]["label_confs"].get(label, 0.0), 
            conf
        )

        for raw_label in span.get("raw_labels", []) or []:
            if raw_label not in merged[key]["raw_labels"]:
                merged[key]["raw_labels"].append(raw_label)

    result = list(merged.values())
    result.sort(key=lambda x: (x["start"], x["end"]))
    return result


def merge_adjacent_segments(segments: list) -> list:
    if not segments:
        return []

    merged = [segments[0]]

    for seg in segments[1:]:
        last = merged[-1]
        if last["labels"] == seg["labels"] and last["raw_labels"] == seg["raw_labels"]:
            last["text"] += seg["text"]
        else:
            merged.append(seg)

    return merged


def build_highlighted_html(text: str, spans: list) -> str:
    if not text:
        return '<div class="doc-box"></div>'

    merged_spans = merge_same_range_spans(spans)

    valid_spans = []
    for span in merged_spans:
        start = max(0, min(len(text), int(span["start"])))
        end = max(0, min(len(text), int(span["end"])))
        if start >= end:
            continue

        valid_spans.append(
            {
                "start": start,
                "end": end,
                "labels": span["labels"] if span["labels"] else ["Other"],
                "label_confs": span["label_confs"],
                "raw_labels": span["raw_labels"],
            }
        )

    boundaries = {0, len(text)}
    for span in valid_spans:
        boundaries.add(span["start"])
        boundaries.add(span["end"])

    sorted_bounds = sorted(boundaries)

    segments = []
    for i in range(len(sorted_bounds) - 1):
        seg_start = sorted_bounds[i]
        seg_end = sorted_bounds[i + 1]
        seg_text = text[seg_start:seg_end]

        active = [
            span for span in valid_spans
            if span["start"] <= seg_start and span["end"] >= seg_end
        ]

        if active:
            segment_confs = {}
            for span in active:
                for lbl, conf in span["label_confs"].items():
                    segment_confs[lbl] = max(segment_confs.get(lbl, 0.0), conf)
            
            labels = sorted(segment_confs.keys(), key=lambda l: segment_confs[l], reverse=True)
            raw_labels = sorted({rl for span in active for rl in span["raw_labels"]})
        else:
            labels = []
            raw_labels = []

        segments.append(
            {
                "text": seg_text,
                "labels": labels,
                "raw_labels": raw_labels,
            }
        )

    segments = merge_adjacent_segments(segments)

    html_parts = ['<div class="doc-box">']

    for seg in segments:
        escaped_text = html.escape(seg["text"]).replace("\n", "<br>")

        if not seg["labels"]:
            html_parts.append(escaped_text)
            continue

        primary_label = seg["labels"][0]
        css_class = css_label_name(primary_label)
        extra_class = " hl-multi" if len(seg["labels"]) > 1 else ""

        tooltip_parts = [f"Labels: {', '.join(seg['labels'])}"]
        if seg["raw_labels"]:
            tooltip_parts.append(f"Raw labels: {', '.join(seg['raw_labels'])}")

        tooltip = html.escape(" | ".join(tooltip_parts))

        html_parts.append(
            f'<span class="hl hl-{css_class}{extra_class}" title="{tooltip}">{escaped_text}</span>'
        )

    html_parts.append("</div>")
    return "".join(html_parts)


def count_items_by_category(grouped_items: dict) -> dict:
    return {label: len(items) for label, items in grouped_items.items()}


def build_fhirish_bundle(doc: dict) -> dict:
    """Approximate FHIR-like export for demo purposes."""
    doc_id = str(doc.get("doc_id", "unknown"))
    grouped_items = doc.get("grouped_items", {})

    entries = []
    idx = 1

    for label, items in grouped_items.items():
        for item in items:
            if label == "Medication":
                resource = {
                    "resourceType": "MedicationRequest",
                    "id": f"{doc_id}-med-{idx}",
                    "status": "active",
                    "intent": "order",
                    "note": [{"text": item}],
                }
            elif label in ["Lab", "Imaging", "Procedure", "Appointment"]:
                resource = {
                    "resourceType": "ServiceRequest",
                    "id": f"{doc_id}-svc-{idx}",
                    "status": "active",
                    "intent": "order",
                    "category": [{"text": label}],
                    "code": {"text": item},
                }
            else:
                resource = {
                    "resourceType": "Communication",
                    "id": f"{doc_id}-comm-{idx}",
                    "status": "completed",
                    "payload": [{"contentString": item}],
                    "category": [{"text": label}],
                }

            entries.append({"resource": resource})
            idx += 1

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "identifier": {"value": f"clip-doc-{doc_id}"},
        "entry": entries,
    }


def render_action_items_panel(doc: dict):
    grouped_items = doc.get("grouped_items", {})
    doc_id = doc.get("doc_id", "")

    st.markdown('<div class="side-panel">', unsafe_allow_html=True)
    st.subheader("Action Items")
    render_metrics_bar(grouped_items)

    raw_json = json.dumps(doc, ensure_ascii=False, indent=2)
    fhir_bundle = build_fhirish_bundle(doc)
    fhirish_json = json.dumps(fhir_bundle, ensure_ascii=False, indent=2)
    resource_count = len(fhir_bundle.get("entry", []))

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "⬇ Download JSON",
            data=raw_json,
            file_name=f"doc_{doc_id}.json",
            mime="application/json",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            f"⬇ FHIR Bundle ({resource_count})",
            data=fhirish_json,
            file_name=f"doc_{doc_id}_fhir.json",
            mime="application/json",
            use_container_width=True,
        )

    # FHIR export preview
    if resource_count > 0:
        # Resource type summary
        type_counts = {}
        for entry in fhir_bundle.get("entry", []):
            rtype = entry.get("resource", {}).get("resourceType", "Unknown")
            type_counts[rtype] = type_counts.get(rtype, 0) + 1
        type_summary = " · ".join(f"{v} {k}" for k, v in type_counts.items())
        with st.expander(f"🔥 FHIR Preview — {type_summary}"):
            st.json(fhir_bundle)

    for label, items in grouped_items.items():
        icon = LABEL_ICONS.get(label, "")
        with st.expander(f"{icon} {label} ({len(items)})", expanded=(len(items) > 0)):
            if items:
                for i, item in enumerate(items, start=1):
                    st.markdown(f"**{i}.** {item}")
            else:
                st.caption("No items in this category.")

    st.markdown('</div>', unsafe_allow_html=True)


def render_evidence_panel(doc: dict):
    doc_id = doc.get("doc_id", "")
    text = doc.get("text", "")
    spans = doc.get("spans", [])

    st.subheader("Evidence")
    st.write("Detected follow-up instructions highlighted in the original text.")
    render_legend()
    st.markdown(build_highlighted_html(text, spans), unsafe_allow_html=True)

    with st.expander("View raw text"):
        st.text_area(
            "Original content",
            value=text,
            height=320,
            key=f"text_{doc_id}",
        )







# ═══════════════════════════════════════════════════════════════════
# TAB 1: AI Inference (primary experience)
# ═══════════════════════════════════════════════════════════════════
with tab1:
    # ── Hero introduction ──────────────────────────────────────────
    st.markdown("""
    <div class="hero-card">
        <h3>📝 Paste a Discharge Summary</h3>
        <p>
            Enter or paste any clinical discharge note below. The AI model will
            automatically identify and categorise follow-up action items —
            medications, appointments, labs, imaging, procedures, and patient
            instructions.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Example cards ──────────────────────────────────────────────
    EXAMPLE_META = {
        "Heart Failure": {
            "icon": "❤️",
            "desc": "Medication titration, lab follow-up, cardiology appointment",
            "tags": "💊 Medication · 🔬 Lab · 📅 Appointment · 📋 Instructions",
        },
        "Pneumonia": {
            "icon": "🫁",
            "desc": "Antibiotic course, inhaler, chest X-ray follow-up",
            "tags": "💊 Medication · 📷 Imaging · 📅 Appointment · 📋 Instructions",
        },
        "Post-Surgical": {
            "icon": "🔪",
            "desc": "Post-op care, wound check, labs, abdominal ultrasound",
            "tags": "📅 Appointment · 🔬 Lab · 📷 Imaging · 📋 Instructions",
        },
    }

    st.markdown('<p class="example-label">Quick examples — click to load:</p>', unsafe_allow_html=True)
    example_cols = st.columns(len(EXAMPLE_TEXTS))
    for col, (name, text) in zip(example_cols, EXAMPLE_TEXTS.items()):
        meta = EXAMPLE_META.get(name, {})
        with col:
            if st.button(
                f"{meta.get('icon', '📄')} {name}",
                use_container_width=True,
                help=meta.get("desc", ""),
            ):
                st.session_state["infer_text"] = text

    # ── Text input ─────────────────────────────────────────────────
    infer_text = st.text_area(
        "Paste discharge summary here:",
        height=320,
        key="infer_text",
        placeholder=(
            "DISCHARGE SUMMARY: [Patient demographics and hospital course...]\n\n"
            "Discharge Instructions:\n"
            "— Continue [medication] [dosage] [frequency] for [duration]\n"
            "— Follow up with [specialty] in [timeframe]\n"
            "— Obtain [lab/imaging] in [timeframe]\n"
            "— Return to ED for [warning signs]\n\n"
            "Tip: the model works best with structured discharge summaries "
            "containing clear section headers."
        ),
    )

    # Word count hint
    if infer_text:
        word_count = len(infer_text.split())
        char_count = len(infer_text)
        if char_count > 50000:
            length_hint = "🚫 Exceeds 50,000 character limit"
        elif char_count > 15000:
            length_hint = "⚠️ Long text — processing may take longer"
        elif word_count > 20:
            length_hint = "✅ Good length"
        else:
            length_hint = "⚠️ Very short — try pasting a full discharge summary"
        st.markdown(
            f'<div class="input-hint">'
            f'<span>{word_count} words · {char_count} characters</span>'
            f'<span>{length_hint}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if st.button("🔍 Analyze Discharge Summary", use_container_width=True, type="primary"):
        if not infer_text.strip():
            st.warning("Please enter text to analyze.")
        elif len(infer_text) > 50000:
            st.error("Text exceeds 50,000 character limit. Please shorten your input.")
        else:
            try:
                import time as _time
                t0 = _time.time()
                with st.status("Analyzing discharge summary...", expanded=True) as status:
                    st.write("📄 Parsing document sections...")
                    _time.sleep(0.3)
                    st.write("✂️ Segmenting sentences...")
                    _time.sleep(0.2)
                    st.write("🧠 Running BioBERT classifier...")
                    result = post_json("/clip/infer", {"text": infer_text})
                    st.write("✅ Generating action items...")
                    _time.sleep(0.2)
                    status.update(label="Analysis complete!", state="complete", expanded=False)
                elapsed = _time.time() - t0

                st.session_state["infer_result"] = result
                st.session_state["infer_input_text"] = infer_text
                st.session_state["infer_elapsed"] = elapsed
            except Exception as e:
                st.error(f"Inference error: {e}")

    infer_result = st.session_state.get("infer_result")
    infer_input = st.session_state.get("infer_input_text", "")
    elapsed = st.session_state.get("infer_elapsed", 0)

    if infer_result is not None:
        grouped_items = infer_result.get("grouped_items", {})
        total = sum(len(items) for items in grouped_items.values())
        cats = sum(1 for items in grouped_items.values() if items)

        # ── Stats card ─────────────────────────────────────────────
        cat_icons = []
        for cat_name, items in grouped_items.items():
            if items:
                icon = LABEL_ICONS.get(cat_name, "📝")
                cat_icons.append(f"{icon} {cat_name} ({len(items)})")
        breakdown = " · ".join(cat_icons)

        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-row">
                <div class="stat-item">
                    <span class="stat-value">{total}</span>
                    <span class="stat-label">Action Items</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{cats}</span>
                    <span class="stat-label">Categories</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{elapsed:.1f}s</span>
                    <span class="stat-label">Processing Time</span>
                </div>
            </div>
            <div style="margin-top: 0.6rem; font-size: 0.82rem; color: #475569;">
                {breakdown}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        left, right = st.columns([1.5, 1], gap="large")

        with left:
            spans = infer_result.get("spans", [])
            st.subheader("Evidence")
            st.write("Detected items highlighted in the original text.")
            render_legend()
            st.markdown(
                build_highlighted_html(infer_input, spans),
                unsafe_allow_html=True,
            )

        with right:
            infer_doc = {
                "doc_id": "infer",
                "grouped_items": grouped_items,
            }
            render_action_items_panel(infer_doc)

        # Sentence detail
        st.subheader("Classified Sentences")
        sentences = infer_result.get("sentences", [])
        if sentences:
            for i, sent in enumerate(sentences, start=1):
                labels_str = ", ".join(sent.get("labels", []))
                icons = " ".join(LABEL_ICONS.get(l, "") for l in sent.get("labels", []))
                with st.expander(f"{i}. {icons} [{labels_str}] {sent['sentence'][:80]}..."):
                    st.markdown(f"**Sentence:** {sent['sentence']}")

                    # Confidence bars per label
                    for lbl in sent.get("labels", []):
                        conf = sent.get("confidences", {}).get(lbl, 0.0)
                        pct = int(conf * 100)
                        icon = LABEL_ICONS.get(lbl, "📝")
                        color = LABEL_COLORS.get(lbl, "#94a3b8")
                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:0.5rem;margin:0.25rem 0;">'
                            f'<span style="min-width:160px;font-size:0.82rem;font-weight:500;">{icon} {lbl}</span>'
                            f'<div style="flex:1;background:#f1f5f9;border-radius:4px;height:8px;overflow:hidden;">'
                            f'<div style="width:{pct}%;height:100%;background:{color};border-radius:4px;"></div>'
                            f'</div>'
                            f'<span style="font-size:0.82rem;font-weight:600;min-width:40px;">{conf:.0%}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
        else:
            st.info("No follow-up instructions detected in this text.")

        # ── Reference & Debug ─────────────────────────────────────────
        st.divider()

        with st.expander("📖 Label Definitions (CLIP Dataset)"):
            st.markdown("""
The model classifies sentences using label definitions from the
[**CLIP** (Clinical Language Inference from Practice)](https://physionet.org/content/mimic-iii-clinical-action/1.0.0/)
dataset. Each label represents an actionable follow-up item for the **primary care physician (PCP)**:

| Label | Definition | Example |
|---|---|---|
| 📋 **Patient Instructions** | Post-discharge instructions directed to the patient, so the PCP can ensure the patient understands and performs them. | *No driving until post-op visit and you are no longer taking pain medications.* |
| 📅 **Appointment** | Appointments to be made by the PCP, or monitored to ensure the patient attends them. | *The patient requires a neurology consult at XYZ for evaluation.* |
| 💊 **Medication** | Medications that the PCP needs to ensure the patient is taking correctly, e.g. time-limited or new medications that may need dose adjustment. | *The patient was instructed to hold ASA and refrain from NSAIDs for 2 weeks.* |
| 🔬 **Lab** | Laboratory tests with results pending or that need to be ordered by the PCP. | *We ask that the patient's family physician repeat these tests in 2 weeks.* |
| 🏥 **Procedure** | Procedures the PCP needs to order, ensure another caregiver orders, or ensure the patient undergoes. | *Please follow-up for EGD with GI.* |
| 📷 **Imaging** | Imaging studies with results pending or that need to be ordered by the PCP. | *Follow-up for resolution recommended to exclude possible malignancy.* |
| 📝 **Other** | Other actionable information important to relay to the PCP. | *We will monitor his nutritional status and trend weights closely.* |
            """)

        with st.expander("🔧 View raw JSON response"):
            st.json(infer_result)



# ═══════════════════════════════════════════════════════════════════
# TAB 3: Architecture
# ═══════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("NLP Pipeline Architecture")
    st.write(
        "This diagram shows how the system processes raw discharge summaries "
        "into structured, actionable clinical follow-up items."
    )

    # Pipeline steps as individual markdown calls
    PIPELINE_STEPS = [
        ("📄", "1. Raw Discharge Summary",
         "Free-text clinical note with demographics, hospital course, and discharge instructions",
         "Input: plain text (any length)"),
        ("📑", "2. Section-Aware Parsing",
         "Identifies section headers (Discharge Instructions, Medications, Follow-up) and filters out narrative sections to focus on actionable content",
         "Regex patterns · Inline header detection (MIMIC-III)"),
        ("✂️", "3. Sentence Segmentation",
         "Splits actionable text into individual sentences, reconstructing line-wrapped text common in clinical notes",
         "Heuristic splitter · Line-wrap reconstruction"),
        ("🧠", "4. Multi-Label Classification",
         "Each sentence is encoded into a 768-dim vector by a fine-tuned BioBERT model, then classified into 7 action types with per-label confidence thresholds",
         "BioBERT (fine-tuned) · Sentence Transformers · Logistic Regression"),
        ("✅", "5. Structured Action Items",
         "Classified sentences are grouped by category, highlighted in the original text, and optionally exported as FHIR R4 resources",
         "Output: JSON · FHIR Bundle · Highlighted text"),
    ]

    for i, (icon, title, desc, tech) in enumerate(PIPELINE_STEPS):
        st.markdown(
            f'<div class="pipeline-step">'
            f'<div class="pipeline-icon">{icon}</div>'
            f'<div class="pipeline-info">'
            f'<div class="pipeline-title">{title}</div>'
            f'<div class="pipeline-desc">{desc}</div>'
            f'<div class="pipeline-tech">{tech}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        if i < len(PIPELINE_STEPS) - 1:
            st.markdown('<div class="pipeline-arrow">↓</div>', unsafe_allow_html=True)

    st.divider()

    # Tech stack and model details
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
<div style="max-width:420px;margin-left:auto;">
<h4 style="margin:0 0 1rem 0;font-size:1rem;">🔧 Tech Stack</h4>
<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
<tr style="border-bottom:2px solid #e2e8f0;"><th style="text-align:left;padding:0.5rem 0.5rem;color:#64748b;width:40%;">Component</th><th style="text-align:left;padding:0.5rem 0.5rem;color:#64748b;">Technology</th></tr>
<tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:0.45rem 0.5rem;font-weight:600;">Language Model</td><td style="padding:0.45rem 0.5rem;">BioBERT (fine-tuned on CLIP)</td></tr>
<tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:0.45rem 0.5rem;font-weight:600;">Embeddings</td><td style="padding:0.45rem 0.5rem;">Sentence Transformers (768-dim)</td></tr>
<tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:0.45rem 0.5rem;font-weight:600;">Classifier</td><td style="padding:0.45rem 0.5rem;">Logistic Regression (multi-label)</td></tr>
<tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:0.45rem 0.5rem;font-weight:600;">Backend API</td><td style="padding:0.45rem 0.5rem;">FastAPI (Python)</td></tr>
<tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:0.45rem 0.5rem;font-weight:600;">Frontend</td><td style="padding:0.45rem 0.5rem;">Streamlit</td></tr>
<tr><td style="padding:0.45rem 0.5rem;font-weight:600;">Deployment</td><td style="padding:0.45rem 0.5rem;">Docker Compose</td></tr>
</table>
</div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
<div style="max-width:420px;">
<h4 style="margin:0 0 1rem 0;font-size:1rem;">📊 Model Details</h4>
<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
<tr style="border-bottom:2px solid #e2e8f0;"><th style="text-align:left;padding:0.5rem 0.5rem;color:#64748b;width:40%;">Parameter</th><th style="text-align:left;padding:0.5rem 0.5rem;color:#64748b;">Value</th></tr>
<tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:0.45rem 0.5rem;font-weight:600;">Training Dataset</td><td style="padding:0.45rem 0.5rem;">CLIP (PhysioNet)</td></tr>
<tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:0.45rem 0.5rem;font-weight:600;">Labels</td><td style="padding:0.45rem 0.5rem;">7 action types</td></tr>
<tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:0.45rem 0.5rem;font-weight:600;">Thresholds</td><td style="padding:0.45rem 0.5rem;">Per-label optimized</td></tr>
<tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:0.45rem 0.5rem;font-weight:600;">Input</td><td style="padding:0.45rem 0.5rem;">Discharge summaries</td></tr>
<tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:0.45rem 0.5rem;font-weight:600;">Output</td><td style="padding:0.45rem 0.5rem;">Multi-label classification</td></tr>
<tr><td style="padding:0.45rem 0.5rem;font-weight:600;">Interoperability</td><td style="padding:0.45rem 0.5rem;">FHIR R4 Bundle export</td></tr>
</table>
</div>
        """, unsafe_allow_html=True)