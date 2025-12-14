import requests
import json

# Étape 3a : Choisir la famille ou l'espèce
taxon_key = 319  # Rosaceae
limit = 10       # nombre d'observations à récupérer

# Étape 3b : Construire l'URL de l'API GBIF
url = f"https://api.gbif.org/v1/occurrence/search?taxonKey={taxon_key}&mediaType=StillImage&limit={limit}"

# Étape 3c : Envoyer la requête
response = requests.get(url)
data = response.json()  # JSON brut des observations

# Étape 3d : Filtrer et créer des fiches JSON
plants = []
for obs in data.get('results', []):
    plant = {
        "nomScientifique": obs.get("species"),
        "nomCommun": obs.get("vernacularName"),
        "famille": obs.get("family"),
        "genre": obs.get("genus"),
        "image": obs.get("media")[0]["identifier"] if obs.get("media") else None,
        "coordonnees": {
            "latitude": obs.get("decimalLatitude"),
            "longitude": obs.get("decimalLongitude")
        },
        "source": obs.get("datasetName")
    }
    plants.append(plant)

# Étape 3e : Sauvegarder en JSON
with open("data/plants_gbif.json", "w", encoding="utf-8") as f:
    json.dump(plants, f, ensure_ascii=False, indent=2)

print(f"{len(plants)} plantes récupérées et sauvegardées dans data/plants_gbif.json")
