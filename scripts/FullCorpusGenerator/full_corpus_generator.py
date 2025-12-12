import os
import json
import pdfplumber
import re

# -----------------------------
# CONFIGURATION
# -----------------------------

JSON_FOLDER = "../../docs/Plantes"     # ← change this
PDF_FOLDER  = "../../docs/Concepts"      # ← change this
OUTPUT_FILE = "../../docs/FullCorpus/fullCorpus.json"

# -----------------------------
# HELPERS
# -----------------------------

def load_json_file(path):
    """
    Loads any JSON file and tries to extract textual content.
    - If file is a list or dict, convert values to a text block.
    - If file contains nested structures, flatten.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        return ""

    def extract_text(obj):
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            return " ".join(extract_text(v) for v in obj.values())
        if isinstance(obj, list):
            return " ".join(extract_text(v) for v in obj)
        return ""

    return extract_text(data)


def load_pdf_file(path):
    """
    Extracts all text from a PDF using pdfplumber.
    """
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join((page.extract_text() or "") for page in pdf.pages)
        return text
    except:
        return ""


def clean_text(text):
    """
    Basic normalization: remove excessive spaces, normalize newlines.
    """
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# -----------------------------
# MAIN MERGE PROCESS
# -----------------------------

all_docs = {}
doc_counter = 1

print("📌 Loading JSON documents...")
for filename in os.listdir(JSON_FOLDER):
    if filename.lower().endswith(".json"):
        path = os.path.join(JSON_FOLDER, filename)
        raw_text = load_json_file(path)
        cleaned_text = clean_text(raw_text)

        doc_id = f"doc_{doc_counter:03d}"
        all_docs[doc_id] = {
            "filename": filename,
            "source_type": "json",
            "text": cleaned_text
        }
        doc_counter += 1

print(f"✔ Loaded {doc_counter-1} JSON files\n")

print("📌 Loading PDF documents...")
for filename in os.listdir(PDF_FOLDER):
    if filename.lower().endswith(".pdf"):
        path = os.path.join(PDF_FOLDER, filename)
        raw_text = load_pdf_file(path)
        cleaned_text = clean_text(raw_text)

        doc_id = f"doc_{doc_counter:03d}"
        all_docs[doc_id] = {
            "filename": filename,
            "source_type": "pdf",
            "text": cleaned_text
        }
        doc_counter += 1

print(f"✔ Loaded {doc_counter-1} documents total (JSON + PDF)\n")

# -----------------------------
# SAVE OUTPUT
# -----------------------------

print(f"💾 Writing merged corpus to: {OUTPUT_FILE}")
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_docs, f, indent=2, ensure_ascii=False)

print("🎉 Done — the entire corpus is now in one file!")
