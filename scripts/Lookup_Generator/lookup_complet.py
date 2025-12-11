import json
import os
from collections import defaultdict
import spacy

# --- CONFIGURATION ---
INPUT_FILE = r'docs\Thesaurus\thesaurus_complet.json'
OUTPUT_FILE = r'docs\Lookup\lookup.json'

print("⏳ Chargement du modèle NLP...")
try:
    nlp = spacy.load("fr_core_news_sm", disable=["parser", "ner"])
except OSError:
    print("❌ Modèle manquant. Run: python -m spacy download fr_core_news_sm")
    exit()

# Stop words : Mots vides qu'on ne veut pas indexer seuls
CUSTOM_STOP_WORDS = {
    "cm", "mm", "m", "gr", "kg", "très", "peu", "souvent", "parfois", 
    "usage", "plante", "type", "forme", "ou", "et", "à", "de", "le", "la", "les", "un", "une", "des",
    "appelé", "appelées", "plus", "tout", "toute"
}

def load_json(path):
    if not os.path.exists(path): return None
    with open(path, 'r', encoding='utf-8') as f: return json.load(f)

def extract_keywords_from_phrase(phrase):
    """
    Cette fonction transforme une phrase longue en mots-clés utiles.
    Entrée : "fleur bleu pâle à blanc"
    Sortie : ["fleur", "bleu", "pâle", "blanc", "fleur bleu"]
    """
    if not phrase: return []
    
    doc = nlp(str(phrase))
    tokens_propres = []
    
    # 1. Extraction des mots simples (Unigrammes)
    for token in doc:
        if not token.is_stop and not token.is_punct and len(token.text) > 1:
            if token.text.lower() not in CUSTOM_STOP_WORDS:
                tokens_propres.append(token.lemma_.lower())
    
    # 2. Création de Bigrammes (Paires de mots) - TRÈS UTILE pour "fleur jaune"
    # On combine les mots qui se suivent s'ils sont pertinents
    bigrammes = []
    if len(tokens_propres) > 1:
        for i in range(len(tokens_propres) - 1):
            w1 = tokens_propres[i]
            w2 = tokens_propres[i+1]
            # On évite de créer des bigrammes bizarres si les mots sont trop génériques
            bigrammes.append(f"{w1} {w2}")
            
    return tokens_propres + bigrammes

def generate_smart_index(thesaurus_data):
    index = defaultdict(set)
    print("⚙️  Génération de l'index avec décomposition des phrases...")

    total = len(thesaurus_data)
    processed = 0

    for concept_id, content in thesaurus_data.items():
        processed += 1
        if processed % 100 == 0: print(f"   Traitement {processed}/{total}...")

        # Liste de tout ce qu'on doit analyser pour ce concept
        raw_inputs = set()
        
        # 1. Le concept principal
        raw_inputs.add(concept_id)
        
        # 2. Les Synonymes (UF) - Souvent courts, on les garde tels quels ET on les découpe
        for uf in content.get('UF', []):
            raw_inputs.add(uf)
            
        # 3. Les Relations (RT) - C'est là que sont tes phrases longues !
        for rt in content.get('RT', []):
            raw_inputs.add(rt)

        # 4. Traitement de chaque entrée (phrase ou mot)
        for text in raw_inputs:
            if not text: continue
            
            # A. On garde la phrase exacte SI elle est courte (max 3 mots)
            # Ex: "fleur jaune" -> OK. "fleur jaune avec des taches..." -> NON
            if len(text.split()) <= 3:
                index[text.lower().strip()].add(concept_id)
            
            # B. On découpe la phrase en mots-clés atomiques
            keywords = extract_keywords_from_phrase(text)
            
            for kw in keywords:
                index[kw].add(concept_id)

    # Nettoyage et tri
    return {k: sorted(list(v)) for k, v in index.items()}

def main():
    data = load_json(INPUT_FILE)
    if not data: return
    
    final_index = generate_smart_index(data)
    
    # Aperçu du résultat pour "fleur"
    if "fleur" in final_index:
        print(f"\n🔍 Test : 'fleur' est liée à {len(final_index['fleur'])} plantes.")
    
    # Aperçu du résultat pour "jaune" (qui venait de phrases longues)
    if "jaune" in final_index:
        print(f"🔍 Test : 'jaune' est lié à {len(final_index['jaune'])} plantes.")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_index, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Terminé ! Fichier : {OUTPUT_FILE}")

if __name__ == "__main__":
    main()