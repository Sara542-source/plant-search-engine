import requests
import json
import os

# -------------------------------
# Étape 1 : Vérifier si le fichier existe et le charger
# -------------------------------
gbif_file = "data/plants_gbif.json"
if not os.path.exists(gbif_file):
    print(f"Le fichier {gbif_file} n'existe pas !")
    exit()

with open(gbif_file, "r", encoding="utf-8") as f:
    try:
        plants = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Erreur JSON : {e}")
        exit()

# -------------------------------
# Étape 2 : Fonction pour interroger Wikidata
# -------------------------------
def enrich_wikidata(nom_scientifique):
    """
    Renvoie description courte et image Wikidata pour une plante
    """
    query = f"""
    SELECT ?item ?itemLabel ?itemDescription ?image WHERE {{
      ?item wdt:P225 "{nom_scientifique}".
      OPTIONAL {{ ?item wdt:P18 ?image }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
    }}
    """
    url = "https://query.wikidata.org/sparql"
    try:
        r = requests.get(url, params={"query": query, "format": "json"}, timeout=10)
        r.raise_for_status()
        data = r.json()
        results = data['results']['bindings']
        if results:
            description = results[0].get('itemDescription', {}).get('value', '')
            image_url = results[0].get('image', {}).get('value', '')
            return description, image_url
    except Exception as e:
        print(f"[Wikidata] Erreur pour {nom_scientifique}: {e}")
    return '', ''

# -------------------------------
# Étape 3 : Fonction pour récupérer texte Wikipedia
# -------------------------------
def get_wikipedia_intro(nom_scientifique):
    """
    Renvoie l'introduction Wikipedia pour une plante
    """
    url = f"https://fr.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&titles={nom_scientifique}&format=json"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        pages = data.get('query', {}).get('pages', {})
        page = next(iter(pages.values()))
        texte_brut = page.get('extract', '')
        return texte_brut
    except Exception as e:
        print(f"[Wikipedia] Erreur pour {nom_scientifique}: {e}")
    return ''

# -------------------------------
# Étape 4 : Boucler sur chaque plante pour enrichir
# -------------------------------
for plant in plants:
    nom = plant.get("nomScientifique")
    if not nom:
        continue

    # Enrichir avec Wikidata
    description_courte, image_wikidata = enrich_wikidata(nom)
    plant["descriptionCourte"] = description_courte
    if not plant.get("image"):
        plant["image"] = image_wikidata

    # Enrichir avec Wikipedia
    description_longue = get_wikipedia_intro(nom)
    plant["descriptionLongue"] = description_longue

# -------------------------------
# Étape 5 : Sauvegarder le JSON enrichi
# -------------------------------
output_file = "data/plants_enrichis.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(plants, f, ensure_ascii=False, indent=2)

print(f"{len(plants)} plantes enrichies et sauvegardées dans {output_file}")
