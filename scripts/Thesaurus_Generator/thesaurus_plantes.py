import json
import os
import glob
import re  # Import nécessaire pour les expressions régulières

# Configuration
INPUT_DIR = './docs/Plantes'
OUTPUT_FILE = './docs/Thesaurus/thesaurus_plantes.json'

def clean_text(text):
    """Nettoyage basique : minuscule et strip"""
    if isinstance(text, str):
        return text.strip().lower()
    return ""


def extract_smart_keywords(text):
    """
    Découpe une phrase longue en mots-clés pertinents pour la recherche.
    Retourne un set de termes nettoyés.
    """
    if not isinstance(text, str):
        return set()

    keywords = set()
    
    # 1. Supprimer le contenu entre parenthèses (ex: "(souvent cultivée...)")
    # Le pattern r'\(.*?\)' cherche les parenthèses et leur contenu
    text_clean = re.sub(r'\(.*?\)', '', text)
    
    # 2. Découper par les virgules (pour les listes d'attributs)
    chunks = text_clean.split(',')
    
    for chunk in chunks:
        token = chunk.strip().lower()
        
        # --- FILTRES DE QUALITÉ ---
        
        # Ignorer si vide
        if not token:
            continue
            
        # Ignorer si contient des chiffres (ex: "30 à 100 cm", "2 ans")
        # On veut des mots, pas des mesures dans le thésaurus sémantique
        if any(char.isdigit() for char in token):
            continue
            
        # Ignorer si la phrase est trop longue (> 5 mots)
        # Ex: "pousse dans les endroits humides et ombragés" -> Trop complexe pour un keyword simple
        if len(token.split()) > 5:
            continue
            
        # Si tout est bon, on garde
        keywords.add(token)
        
    return keywords

def process_plant_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        infos = data.get('infos_generales', {})
        utilisations = data.get('utilisations', {})
        attributs = data.get('attributs_specifiques', {})
        caracteristiques = data.get('caracteristiques', {})

        raw_scientific_name = infos.get('nom_scientifique')
        if not raw_scientific_name: return None
        
        entry_id = clean_text(raw_scientific_name)

        # Initialisation
        alt_labels = set()
        broader = set()
        related = set()
        flags = set()

        # --- AltLabels ---
        if infos.get('nom_commun'): alt_labels.add(clean_text(infos['nom_commun']))
        for lst in [infos.get('noms_darija', []), infos.get('noms_alternatifs', [])]:
            if isinstance(lst, list):
                for name in lst: alt_labels.add(clean_text(name))

        # --- Broader ---
        if infos.get('famille'): broader.add(clean_text(infos['famille']))
        if infos.get('genre'): broader.add(clean_text(infos['genre']))

        # --- Related (AVEC SMART EXTRACTION) ---
        
        # 1. Utilisations
        for category, usages in utilisations.items():
            if isinstance(usages, list):
                for usage in usages:
                    # On applique l'extraction intelligente ici aussi
                    related.update(extract_smart_keywords(usage))

        # 2. Régions
        regions = caracteristiques.get('regions_origine', [])
        if isinstance(regions, list):
            for region in regions:
                related.update(extract_smart_keywords(region))

        # 3. Attributs Spécifiques
        for key, value in attributs.items():
            key_clean = clean_text(key)
            
            # Extraction des mots clés de la valeur (ex: "jaune, vert")
            val_keywords = extract_smart_keywords(value)
            
            if not val_keywords: continue

            # Ajout des mots clés bruts + contextuels
            for kw in val_keywords:
                related.add(kw)  # ex: "jaune"
                
                if "couleur" in key_clean or "fleur" in key_clean:
                    related.add(f"fleur {kw}")
                elif "odeur" in key_clean:
                    related.add(f"odeur {kw}")

        # --- Flags ---
        is_toxic = caracteristiques.get('toxicite')
        if is_toxic is False:
            flags.add("comestible")
            flags.add("non toxique")
        elif is_toxic is True:
            flags.add("toxique")

        return {
            "id": entry_id,
            "data": {
                "prefLabel": entry_id,
                "altLabels": list(alt_labels),
                "broader": list(broader),
                "related": list(related),
                "flags": list(flags)
            }
        }

    except Exception as e:
        print(f"Erreur sur {file_path}: {e}")
        return None

def main():
    if not os.path.exists(INPUT_DIR): return
    files = glob.glob(os.path.join(INPUT_DIR, '*.json'))
    thesaurus = {}
    
    for file_path in files:
        res = process_plant_file(file_path)
        if res: thesaurus[res['id']] = res['data']

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(thesaurus, f, indent=4, ensure_ascii=False)
    print(f"✅ Thésaurus nettoyé généré : {OUTPUT_FILE}")

if __name__ == "__main__":
    main()