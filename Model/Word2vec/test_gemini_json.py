import json
import os

# --- Schéma général attendu ---
SCHEMA = {
    "id": str,
    "infos_generales": {
        "nom_scientifique": str,
        "nom_commun": str,
        "noms_darija": list,
        "noms_alternatifs": list,
        "famille": str,
        "genre": str
    },
    "galerie_images": list,
    "caracteristiques": {
        "arrosage": str,
        "luminosite": str,
        "type_sol": str,
        "regions_origine": list,
        "toxicite": bool
    },
    "attributs_specifiques": {
        "feuillage": str,
        "odeur": str,
        "taille_maximale": str,
        "floraison": str
    },
    "utilisations": {
        "medicale": list,
        "culinaire": list,
        "decoration": list
    },
    "source_data": {
        "resume": str,
        "texte_complet": {
            "metadata": {
                "extracted_date": str,
                "total_sections": int,
                "max_depth": int
            },
            "introduction": str,
            "sections": list
        },
        "urls": {
            "trefle": str,
            "wikipedia": str
        }
    }
}

# --- Valeurs autorisées pour certaines listes ---
ALLOWED_ARROSAGE = ["Faible", "Moyen", "Élevé"]
ALLOWED_LUMINOSITE = ["Plein soleil", "Mi-ombre", "Ombre"]

def validate_section(section, path="root"):
    """Validation récursive des sections de texte_complet"""
    required_keys = ["id", "level", "title", "content", "children"]
    for key in required_keys:
        if key not in section:
            print(f"❌ Champ manquant dans {path}: {key}")
            return False
    # Types
    if not isinstance(section["id"], str):
        print(f"❌ {path}.id doit être une string")
        return False
    if not isinstance(section["level"], int):
        print(f"❌ {path}.level doit être un int")
        return False
    if not isinstance(section["title"], str):
        print(f"❌ {path}.title doit être une string")
        return False
    if not isinstance(section["content"], str):
        print(f"❌ {path}.content doit être une string")
        return False
    if not isinstance(section["children"], list):
        print(f"❌ {path}.children doit être une liste")
        return False
    # Validation récursive des enfants
    for i, child in enumerate(section["children"]):
        if not validate_section(child, path=f"{path}.children[{i}]"):
            return False
    return True

def test_json(json_path):
    if not os.path.exists(json_path):
        print(f"❌ Fichier introuvable: {json_path}")
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    def check_schema(obj, schema, path="root"):
        if isinstance(schema, dict):
            if not isinstance(obj, dict):
                print(f"❌ {path} n'est pas un dict")
                return False
            for key, val_type in schema.items():
                if key not in obj:
                    print(f"❌ Champ manquant : {path}.{key}")
                    return False
                if not check_schema(obj[key], val_type, path + "." + key):
                    return False
        elif isinstance(schema, list):
            if not isinstance(obj, list):
                print(f"❌ {path} n'est pas une liste")
                return False
        else:
            if not isinstance(obj, schema):
                print(f"❌ {path} n'est pas du type {schema.__name__}")
                return False
        return True

    # --- Vérification du schéma principal ---
    if not check_schema(data, SCHEMA):
        print("❌ Échec validation schéma")
        return False
    print("✅ Schéma principal validé")

    # --- Vérification valeurs autorisées ---
    if data["caracteristiques"]["arrosage"] not in ALLOWED_ARROSAGE:
        print("❌ Valeur d'arrosage invalide :", data["caracteristiques"]["arrosage"])
        return False
    if data["caracteristiques"]["luminosite"] not in ALLOWED_LUMINOSITE:
        print("❌ Valeur de luminosité invalide :", data["caracteristiques"]["luminosite"])
        return False
    print("✅ Valeurs autorisées OK")

    # --- Vérification images ---
    if not all(isinstance(img, str) for img in data["galerie_images"]):
        print("❌ Certaines images ne sont pas des chaînes de caractères")
        return False
    if len(data["galerie_images"]) == 0:
        print("❌ Galerie d'images vide")
        return False
    print("✅ Images OK")

    # --- Validation sections récursive ---
    for i, section in enumerate(data["source_data"]["texte_complet"]["sections"]):
        if not validate_section(section, path=f"source_data.texte_complet.sections[{i}]"):
            return False

    print("✅ Sections texte_complet validées")
    print("🎉 JSON passé tous les tests !")
    return True

# --- Exemple d'utilisation ---
json_file = "data/romarin.json"  # <-- remplace par ton fichier JSON généré
test_json(json_file)
