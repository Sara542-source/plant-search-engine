import json
import os
from collections import defaultdict
import spacy

# --- Configuration ---
INPUT_FILE = './docs/Thesaurus/thesaurus_plantes.json'
OUTPUT_FILE = './docs/Lookup/lookup_index.json'

# Chargement du modèle NLP français
# "disable" désactive les composants inutiles pour gagner en vitesse (on veut juste tokenizer et lemmatiser)
print("⏳ Chargement du modèle linguistique (spaCy)...")
try:
    nlp = spacy.load("fr_core_news_sm", disable=["parser", "ner"])
except OSError:
    print("❌ Erreur: Le modèle spaCy n'est pas installé.")
    print("👉 Exécute: python -m spacy download fr_core_news_sm")
    exit()

# Tu peux ajouter des stop-words spécifiques à la botanique ici si nécessaire
CUSTOM_STOP_WORDS = {
    "cm", "mm", "m", "gr", "kg", "très", "peu", "souvent", "parfois"
}

def load_json(path):
    if not os.path.exists(path):
        print(f"❌ Fichier introuvable : {path}")
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def tokenize_and_lemmatize(text):
    """
    Utilise spaCy pour :
    1. Tokenizer (découper)
    2. Lemmatiser (racine du mot)
    3. Filtrer (stop words, ponctuation)
    Ex: "Feuilles séchées" -> ["feuille", "sécher"]
    """
    if not text:
        return []

    doc = nlp(text)
    valid_tokens = []

    for token in doc:
        # Filtres : Pas de stop word, pas de ponctuation, pas d'espace
        if not token.is_stop and not token.is_punct and not token.is_space:
            # Vérification supplémentaire avec tes stop words personnalisés
            if token.text.lower() in CUSTOM_STOP_WORDS:
                continue
                
            # On récupère le LEMME (la racine) en minuscule
            lemma = token.lemma_.lower()
            
            # On garde seulement les mots de plus de 1 lettre
            if len(lemma) > 1:
                valid_tokens.append(lemma)
                
    return valid_tokens

def generate_inverted_index(thesaurus_data):
    """
    Construit l'index inversé avec lemmatisation
    """
    index = defaultdict(set)
    
    print("⚙️  Construction de l'index et lemmatisation en cours...")
    
    total_plants = len(thesaurus_data)
    processed = 0

    for plant_id, content in thesaurus_data.items():
        processed += 1
        # Petit indicateur de progression tous les 100 items
        if processed % 100 == 0:
            print(f"   Traitement : {processed}/{total_plants} plantes...")

        terms_to_index = set()
        
        # 1. Collecte de toutes les données textuelles brutes
        terms_to_index.add(content.get('prefLabel', ''))
        terms_to_index.update(content.get('altLabels', []))
        terms_to_index.update(content.get('broader', []))
        terms_to_index.update(content.get('related', []))
        terms_to_index.update(content.get('flags', []))

        # 2. Indexation
        for raw_term in terms_to_index:
            if not raw_term: continue
            
            clean_raw = raw_term.strip().lower()
            
            # 1. Traitement des LEMMES (Priorité absolue)
            lemmas = tokenize_and_lemmatize(clean_raw)
            if lemmas:
                for lemma in lemmas:
                    index[lemma].add(plant_id)
            
            # 2. Traitement des PHRASES (Expressions composées)
            # On ne garde la forme brute QUE si c'est une phrase (plusieurs mots)
            # Cela permet de trouver "bords de chemins" exact, mais évite le doublon "brillantes"
            if len(clean_raw.split()) > 1:
                index[clean_raw].add(plant_id)

    # Conversion set -> list et tri
    final_index = {k: list(v) for k, v in index.items()}
    return dict(sorted(final_index.items()))

def main():
    # 1. Chargement
    thesaurus = load_json(INPUT_FILE)
    if not thesaurus: return

    # 2. Génération
    lookup_index = generate_inverted_index(thesaurus)
    
    # 3. Stats
    nb_keywords = len(lookup_index)
    nb_plantes = len(thesaurus)
    
    print("-" * 30)
    print(f"📊 RÉSULTATS :")
    print(f"   🌿 Plantes indexées : {nb_plantes}")
    print(f"   🔑 Entrées dans l'index (Mots + Lemmes) : {nb_keywords}")

    # 4. Sauvegarde
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(lookup_index, f, indent=4, ensure_ascii=False)
        print(f"✅ Fichier sauvegardé : {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Erreur sauvegarde : {e}")

if __name__ == "__main__":
    main()