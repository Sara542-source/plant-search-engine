import json
import os
import glob
import time
import google.generativeai as genai
from pypdf import PdfReader
from google.api_core import exceptions

# --- CONFIGURATION ---
# Remplace par ta vraie clé API
API_KEY = "AIzaSyDsTA_FU083hZINP_uqT9c1RpiatxQ45_s"
genai.configure(api_key=API_KEY)

# Utilisation de Flash (rapide et moins cher)
model = genai.GenerativeModel('gemini-2.5-flash')

# Chemins des dossiers (à adapter)
INPUT_DIR_JSON = 'data/processed'  # Tes 75 fichiers JSON
INPUT_DIR_PDF = 'data/raw'  # Tes fichiers PDF
OUTPUT_FILE = 'llm_extracted.json'  # Fichier de sortie de cette étape


# --- 1. FONCTIONS D'EXTRACTION DE TEXTE ---

def get_all_strings_recursive(data):
    """
    Aspirateur de texte : parcourt toute structure JSON imbriquée (source_data)
    pour extraire le texte, peu importe la structure des sections.
    """
    text_list = []
    if isinstance(data, dict):
        for key, value in data.items():
            # On ignore les URLs et IDs pour ne pas polluer l'IA
            if any(x in key.lower() for x in ["url", "link", "id", "href"]):
                continue
            text_list.extend(get_all_strings_recursive(value))
    elif isinstance(data, list):
        for item in data:
            text_list.extend(get_all_strings_recursive(item))
    elif isinstance(data, str):
        if data.strip() and len(data) > 3:  # On ignore les trucs trop courts
            text_list.append(data)
    return text_list


def extract_text_from_pdf(pdf_path):
    """Extrait le texte brut d'un PDF."""
    text_content = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            t = page.extract_text()
            if t: text_content += t + "\n"
    except Exception as e:
        print(f"Erreur lecture PDF {pdf_path}: {e}")
    return text_content


# --- 2. INTELLIGENCE ARTIFICIELLE (GEMINI) ---

# def ask_gemini_for_terms(text_chunk):
#     """Envoie le texte à Gemini pour identifier les mots à protéger."""
#     if not text_chunk or len(text_chunk) < 50:
#         return []
#
#     prompt = f"""
#     Analyse ce texte botanique et extrais les termes techniques spécifiques.
#
#     Je veux une liste JSON contenant uniquement :
#     1. Les noms scientifiques latins (ex: "Citrus limon").
#     2. Les noms vernaculaires en Darija, Arabe ou Français (ex: "Laymoun", "Zita", "Romarin").
#
#     Règles :
#     - Ne donne PAS d'explications.
#     - Retourne UNIQUEMENT une liste JSON de chaînes de caractères : ["mot1", "mot2"].
#     - Si aucun terme n'est trouvé, retourne [].
#
#     Texte à analyser :
#     "{text_chunk[:10000]}"
#     """
#
#     try:
#         response = model.generate_content(prompt)
#         clean_res = response.text.replace("```json", "").replace("```", "").strip()
#         terms = json.loads(clean_res)
#         return terms if isinstance(terms, list) else []
#     except Exception as e:
#         print(f"Erreur Gemini : {e}")
#         return []

def ask_gemini_for_terms(text_chunk):
    """
    Envoie le texte à Gemini avec une gestion automatique des erreurs de quota (429).
    Si le quota est dépassé, le script attend 60 secondes et réessaie.
    """
    if not text_chunk or len(text_chunk) < 50:
        return []

    prompt = f"""
    Analyse ce texte botanique et extrais les termes techniques spécifiques.

    Je veux une liste JSON contenant uniquement :
    1. Les noms scientifiques latins (ex: "Citrus limon").
    2. Les noms vernaculaires en Darija, Arabe ou Français (ex: "Laymoun", "Zita", "Romarin").

    Règles :
    - Ne donne PAS d'explications.
    - Retourne UNIQUEMENT une liste JSON de chaînes de caractères : ["mot1", "mot2"].
    - Si aucun terme n'est trouvé, retourne [].

    Texte à analyser :
    "{text_chunk[:10000]}"
    """

    # On tente 3 fois maximum avant d'abandonner pour ce fichier
    max_retries = 3
    attempt = 0

    while attempt < max_retries:
        try:
            # Appel à l'API
            response = model.generate_content(prompt)

            # Nettoyage et parsing
            clean_res = response.text.replace("```json", "").replace("```", "").strip()
            terms = json.loads(clean_res)

            # Si succès, on renvoie la liste
            return terms if isinstance(terms, list) else []

        except exceptions.ResourceExhausted:
            # ERREUR 429 : QUOTA DÉPASSÉ
            wait_time = 60  # On attend 1 minute pour être sûr
            print(f"⚠️ Quota atteint (429). Pause de {wait_time}s avant de réessayer...")
            time.sleep(wait_time)
            attempt += 1  # On compte un essai

        except Exception as e:
            # AUTRES ERREURS (ex: JSON malformé, problème réseau)
            print(f"❌ Erreur Gemini (non-quota) : {e}")
            return []  # On abandonne ce fichier et on passe au suivant

    print("❌ Abandon après 3 tentatives échouées sur ce fichier.")
    return []
# --- 3. TRAITEMENT DES MOTS (Ta logique Complète + Composants) ---

def process_and_add_terms(term_list, target_set):
    """Stocke le mot complet ET ses composants individuels."""
    for term in term_list:
        if not term or not isinstance(term, str): continue

        # 1. Forme complète
        clean_term = term.strip()
        target_set.add(clean_term)

        # 2. Composants individuels (split par espace)
        parts = clean_term.split()
        if len(parts) > 1:
            for part in parts:
                # Nettoyage basique de ponctuation si collée (optionnel)
                part = part.strip(".,;:()[]\"'")
                if len(part) > 1:  # Évite les lettres seules
                    target_set.add(part)


# --- 4. EXÉCUTION PRINCIPALE ---

def main():
    protected_terms = set()

    # A. TRAITEMENT DES JSON (source_data uniquement)
    json_files = glob.glob(os.path.join(INPUT_DIR_JSON, "*.json"))
    print(f"--- Début analyse : {len(json_files)} fichiers JSON (source_data) ---")

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extraction récursive dans source_data
            source_content = data.get("source_data", {})
            all_texts = get_all_strings_recursive(source_content)
            full_text = " ".join(all_texts)

            if full_text:
                print(f"-> Envoi Gemini : {os.path.basename(file_path)}")
                extracted = ask_gemini_for_terms(full_text)
                process_and_add_terms(extracted, protected_terms)
                time.sleep(1.5)  # Pause pour respecter le quota API

        except Exception as e:
            print(f"Erreur fichier {file_path}: {e}")

    # B. TRAITEMENT DES PDF
    pdf_files = glob.glob(os.path.join(INPUT_DIR_PDF, "*.pdf"))
    print(f"\n--- Début analyse : {len(pdf_files)} fichiers PDF ---")

    for pdf_path in pdf_files:
        print(f"-> Extraction PDF : {os.path.basename(pdf_path)}")
        raw_text = extract_text_from_pdf(pdf_path)

        if raw_text:
            # On prend les 10 000 premiers caractères (suffisant pour extraire le sujet principal)
            # Tu peux faire une boucle par page si tu veux être exhaustif
            extracted = ask_gemini_for_terms(raw_text)
            process_and_add_terms(extracted, protected_terms)
            time.sleep(1.5)

    # C. SAUVEGARDE
    final_list = list(protected_terms)
    final_list.sort()

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)

    print(f"\nTERMINÉ. {len(final_list)} termes extraits sauvegardés dans '{OUTPUT_FILE}'")


if __name__ == "__main__":
    main()