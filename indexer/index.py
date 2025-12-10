import os
import json
import spacy
from collections import defaultdict
from pypdf import PdfReader
from spacy.language import Language

# --- CONFIGURATION ---
dossier_json = "./data/processed"  # Vos JSON
dossier_pdf = "./data/raw"  # Vos PDF
fichier_sortie = "index_inverse.json"
fichier_mots_proteges = "protected_terms.json"  # Votre liste [ "Moringa oleifera", ... ]

# Champs à IGNORER totalement dans le JSON
CHAMPS_A_IGNORER = {"galerie_images", "urls", "id", "image_url"}

# --- 1. CONFIGURATION SPACY (MODÈLE + PROTECTION) ---

print("Chargement du modèle spaCy...")
nlp = spacy.load("fr_core_news_md")


def charger_config_mots_proteges(chemin_json):
    """Charge les mots protégés depuis le JSON."""
    mon_set_protege = set()
    patterns = []

    if not os.path.exists(chemin_json):
        print(f"ATTENTION : Fichier {chemin_json} absent.")
        return mon_set_protege, patterns

    try:
        with open(chemin_json, 'r', encoding='utf-8') as f:
            liste_mots = json.load(f)
            if isinstance(liste_mots, list):
                for mot in liste_mots:
                    if isinstance(mot, str) and mot.strip():
                        # Nettoyage et ajout au set
                        clean_mot = mot.strip()
                        mon_set_protege.add(clean_mot.lower())
                        patterns.append({"label": "BOTANIQUE", "pattern": clean_mot})
    except Exception as e:
        print(f"Erreur config mots protégés : {e}")

    return mon_set_protege, patterns


# Chargement configuration
protected_set, patterns_botanique = charger_config_mots_proteges(fichier_mots_proteges)

# Ajout EntityRuler (Détection)
if patterns_botanique:
    # phrase_matcher_attr="LOWER" -> insensible à la casse
    ruler = nlp.add_pipe("entity_ruler", before="ner", config={"phrase_matcher_attr": "LOWER"})
    ruler.add_patterns(patterns_botanique)


# Ajout Fusion (Merge) - Transforme "Moringa oleifera" en 1 seul token
@Language.component("fusionner_botanique")
def fusionner_tokens_botanique(doc):
    with doc.retokenize() as retokenizer:
        for ent in doc.ents:
            if ent.label_ == "BOTANIQUE":
                retokenizer.merge(ent)
    return doc


nlp.add_pipe("fusionner_botanique", after="entity_ruler")


# --- 2. EXTRACTION INTELLIGENTE (RECURSIVE) ---

def extraire_json_recursif(data):
    """
    Parcourt n'importe quelle structure JSON (dict, list) en profondeur.
    Ignore les clés définies dans CHAMPS_A_IGNORER.
    Retourne une seule chaîne de texte.
    """
    texte_accumule = ""

    if isinstance(data, dict):
        for key, value in data.items():
            # SI la clé est dans la liste noire, on saute tout son contenu
            if key in CHAMPS_A_IGNORER:
                continue

            # Sinon, on continue de creuser
            texte_accumule += extraire_json_recursif(value)

    elif isinstance(data, list):
        for item in data:
            texte_accumule += extraire_json_recursif(item)

    elif isinstance(data, str):
        # C'est ici qu'on récupère le vrai texte
        texte_accumule += data + " "

    # On ignore les int/float/bool pour l'indexation textuelle

    return texte_accumule


def extraire_texte_pdf(chemin_fichier):
    texte = ""
    try:
        reader = PdfReader(chemin_fichier)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                texte += t + " "
    except Exception as e:
        print(f"Erreur lecture PDF {chemin_fichier}: {e}")
    return texte


# --- 3. TRAITEMENT NLP ---

'''def traiter_texte(texte):
    # Augmenter la limite pour les gros textes concaténés
    nlp.max_length = 2000000

    doc = nlp(texte)
    frequences_doc = defaultdict(int)

    for token in doc:
        if token.is_space:
            continue

        mot_lower = token.text.lower().strip()

        # 1. Protection (Mots simples ou composés fusionnés)
        if mot_lower in protected_set:
            frequences_doc[mot_lower] += 1

        # 2. Lemmatisation standard
        else:
            if not token.is_stop and not token.is_punct and len(mot_lower) > 2:
                # On évite d'indexer les chiffres isolés ou erreurs
                if token.pos_ != "NUM" or token.like_num :
                    frequences_doc[token.lemma_.lower()] += 1

    return frequences_doc

'''
def traiter_texte(texte):
    # Augmenter la limite pour les gros textes concaténés
    nlp.max_length = 2000000

    doc = nlp(texte)
    frequences_doc = defaultdict(int)

    for token in doc:
        # On saute les espaces vides
        if token.is_space:
            continue

        mot_lower = token.text.lower().strip()

        # 1. Protection (Mots botaniques ou protégés)
        if mot_lower in protected_set:
            frequences_doc[mot_lower] += 1

        # 2. Lemmatisation standard
        else:
            # On vérifie d'abord si c'est un mot "inutile" (stop word ou ponctuation)
            if not token.is_stop and not token.is_punct:
                
                # C'EST ICI QUE TOUT SE JOUE :
                
                # Condition A : C'est un nombre ? (On le garde peu importe la longueur)
                is_number = token.like_num
                
                # Condition B : C'est un mot normal ? (Il doit faire plus de 2 lettres)
                is_valid_word = len(mot_lower) > 2
                
                # Si c'est un nombre OU un mot valide
                if is_number or is_valid_word:
                    # ---> C'EST CETTE LIGNE QUI STANDARDISE (VERBES, ADJ, ETC.) <---
                    term_standardise = token.lemma_.lower()
                    frequences_doc[term_standardise] += 1

    return frequences_doc
# --- 4. EXÉCUTION ---

def construire_index():
    index_inverse = defaultdict(dict)

    # A. TRAITEMENT JSON
    if os.path.exists(dossier_json):
        fichiers = [f for f in os.listdir(dossier_json) if f.endswith(".json")]
        print(f"--- Traitement JSON ({len(fichiers)} fichiers) ---")

        for fichier in fichiers:
            path = os.path.join(dossier_json, fichier)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data_json = json.load(f)
                    # APPEL DE LA FONCTION RÉCURSIVE
                    contenu_texte = extraire_json_recursif(data_json)

                    if contenu_texte.strip():
                        freqs = traiter_texte(contenu_texte)
                        for terme, freq in freqs.items():
                            index_inverse[terme][fichier] = freq
                    else:
                        print(f"Attention: Aucun texte extrait de {fichier}")
            except Exception as e:
                print(f"Erreur fichier {fichier}: {e}")

    # B. TRAITEMENT PDF
    if os.path.exists(dossier_pdf):
        fichiers = [f for f in os.listdir(dossier_pdf) if f.endswith(".pdf")]
        print(f"--- Traitement PDF ({len(fichiers)} fichiers) ---")

        for fichier in fichiers:
            path = os.path.join(dossier_pdf, fichier)
            contenu_texte = extraire_texte_pdf(path)

            if contenu_texte.strip():
                freqs = traiter_texte(contenu_texte)
                for terme, freq in freqs.items():
                    index_inverse[terme][fichier] = freq

    return index_inverse


if __name__ == "__main__":
    # Petit check de sécurité
    if not os.path.exists(fichier_mots_proteges):
        print(f"⚠️ Créez '{fichier_mots_proteges}' avec par ex: [\"Moringa oleifera\"]")

    index_final = construire_index()

    with open(fichier_sortie, 'w', encoding='utf-8') as f:
        json.dump(index_final, f, ensure_ascii=False, indent=4)

    print(f"Terminé ! {len(index_final)} termes uniques indexés.")