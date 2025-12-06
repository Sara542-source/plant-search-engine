import os
import json
import time
import google.generativeai as genai
from datetime import datetime

# ==========================================
# 1. CONFIGURATION (À MODIFIER PAR TOI)
# ==========================================

# TA CLÉ API GEMINI (Colle ta clé ici)
GOOGLE_API_KEY = "API"

# Ton fichier d'entrée (la liste des plantes avec IDs et images)
INPUT_FILE_PATH = "plantes_avec_images.json"

# Dossier de sortie (sera créé automatiquement)
OUTPUT_FOLDER = "../Corpus/Plantes"

# Fichier de suivi des erreurs
ERROR_LOG_FILE = "erreurs_generation.txt"

# Modèle Gemini (Flash est rapide, Pro est plus intelligent pour le parsing complexe)
MODEL_NAME = "gemini-2.5-flash"

# ==========================================
# 2. TA PROMPT EXACTE (INTEGRÉE ICI)
# ==========================================
SYSTEM_PROMPT = """
Tu es un expert botanique spécialisé dans la flore d'Afrique du Nord (Maroc) et un architecte de données JSON strict.
TACHE :
À partir de l'objet JSON fourni en entrée (contenant id, liens et images pré-sélectionnées), génère un objet JSON unique final représentant la plante.
RETOURNE UNIQUEMENT LE JSON FINAL EXACTEMENT CONFORME AU SCHÉMA CI-DESSOUS.
N'AJOUTE AUCUN CHAMP SUPPLÉMENTAIRE, N'EN RETIRE AUCUN.
DONNÉES EN ENTRÉE :
Je vais te fournir un objet JSON sous ce format :

JSON

{
    "id": "...",
    "trefle": "...",
    "wiki": "...",
    "images_auto": ["...", "..."]
}
CONSIGNES DE REMPLISSAGE STRICTES :
A. LANGUE & LOCALISATION :

Tout le contenu textuel doit être en FRANÇAIS.
Champ "noms_darija" : Fournis les noms vernaculaires utilisés au Maroc (latin et arabe). Ex: ["Azir", "أزير"].
B. IMAGES ("galerie_images") :

Remplis ce tableau avec les URLs présentes dans le champ images_auto de l'INPUT.
Si images_auto est vide, cherche 2 ou 3 images pertinentes via le lien Trefle ou Wiki.
C. CARACTÉRISTIQUES (Vocabulaire imposé) :

"arrosage" : ["Faible", "Modéré", "Fréquent", "Aquatique"]
"luminosite" : ["Ombre", "Mi-ombre", "Plein soleil"]
"toxicite" : true/false
D. UTILISATIONS (Mapping Vocabulaire Contrôlé) : Mappe les usages vers ces tags EXACTS.

"medicale" : ["Digestif", "Respiratoire", "Dermatologique", "Apaisant", "Tonique", "Antiseptique", "Anti-inflammatoire", "Autre usage médical"].
"culinaire" : ["Infusion", "Épice", "Aromatique", "Salade", "Cuit", "Dessert"].
"decoration" : ["Intérieur", "Jardin", "Haie", "Couvre-sol", "Jardin sec", "Balcon", "Fleurs coupées"].
E. ATTRIBUTS SPÉCIFIQUES :

"attributs_specifiques" : Capture les détails uniques (odeur, type de racines, etc.) en clé/valeur.
SCHEMA JSON CIBLE (Renvoie UNIQUEMENT ce JSON) :
{
"id": "Reprendre l'ID fourni en INPUT",
"infos_generales": {
"nom_scientifique": "String",
"nom_commun": "String",
"noms_darija": [],
"noms_alternatifs": [],
"famille": "String",
"genre": "String"
},
"galerie_images": [],
"caracteristiques": {
"arrosage": "String",
"luminosite": "String",
"type_sol": "String",
"regions_origine": [],
"toxicite": false
},
"attributs_specifiques": {},
"utilisations": {
"medicale": [],
"culinaire": [],
"decoration": []
},
"source_data": {
"resume": "Résumé bref (max 150 mots) du contexte global de la plante",
"texte_complet": {}, // Voir instructions ci-dessous
"urls": {
"trefle": "Reprendre URL trefle de l'INPUT",
"wikipedia": "Reprendre URL wiki de l'INPUT"
}
}
}
INSTRUCTIONS POUR LE CHAMP "texte_complet" (Wikipedia Parsing) :
Agis comme un expert en parsing Wikipedia.

Utilise l'URL fournie dans le champ wiki de l'INPUT.
Extrais tout le contenu de l'article.
EXCLUSION STRICTE : Ne pas inclure les sections : "Notes", "Références", "Bibliographie", "Liens externes", "Voir aussi", "Annexes", "Sources".
Structure du champ "texte_complet" :
{
"introduction": "Texte avant le premier header de section, nettoyé",
"sections": [
{
"id": "slug_unique",
"level": 1,
"title": "Titre section",
"content": "Contenu complet sans markup",
"children": []
}
]
}
"""

# ==========================================
# 3. FONCTIONS UTILITAIRES
# ==========================================

def setup_environment():
    """Initialise l'API et les dossiers."""
    genai.configure(api_key=GOOGLE_API_KEY)
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    # On crée le fichier de log s'il n'existe pas
    if not os.path.exists(ERROR_LOG_FILE):
        with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"LOG CREATION: {datetime.now()}\n")

def clean_json_response(text):
    """Nettoie les balises Markdown ```json que Gemini ajoute souvent."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def log_error(plant_id, error_msg):
    """Enregistre l'erreur dans le fichier et la console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] ERREUR ID {plant_id}: {error_msg}\n"
    print(f"❌ {full_msg.strip()}")
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_msg)

def save_failed_response(plant_id, raw_text):
    """Sauvegarde la réponse brute si le JSON est invalide pour debugging."""
    filename = os.path.join(OUTPUT_FOLDER, f"FAIL_{plant_id}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(raw_text)

# ==========================================
# 4. CŒUR DU TRAITEMENT
# ==========================================

def process_one_plant(plant, model):
    plant_id = plant.get("id", "UNKNOWN")
    output_file = os.path.join(OUTPUT_FOLDER, f"{plant_id}.json")

    if os.path.exists(output_file):
        print(f"⏩ ID {plant_id} existe déjà. Ignoré.")
        return

    print(f"🔄 Traitement ID {plant_id}...")
    user_message = f"VOICI L'OBJET JSON À TRAITER : {json.dumps(plant)}"

    # SYSTEME DE RETRY (Réessai)
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # Appel API
            response = model.generate_content([SYSTEM_PROMPT, user_message])

            # Nettoyage et Sauvegarde
            json_text = clean_json_response(response.text)
            final_data = json.loads(json_text)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)

            print(f"✅ ID {plant_id} généré avec succès.")
            return # On sort de la fonction car c'est réussi

        except Exception as e:
            error_str = str(e)
            # Si c'est une erreur 429 (Quota)
            if "429" in error_str or "quota" in error_str.lower():
                wait_time = 60 # On attend 60 secondes
                print(f"⚠️ Quota dépassé (Tentative {attempt+1}/{max_retries}). Pause de {wait_time}s...")
                time.sleep(wait_time)
            else:
                # Si c'est une autre erreur (ex: JSON invalide), on log et on abandonne cette plante
                log_error(plant_id, f"Erreur non liée au quota: {error_str}")
                return

    # Si on arrive ici, c'est qu'on a échoué 5 fois de suite
    log_error(plant_id, "ECHEC FINAL après 5 tentatives (Quota persistant).")

# ==========================================
# 5. MAIN
# ==========================================

def main():
    setup_environment()

    # Chargement du modèle
    model = genai.GenerativeModel(MODEL_NAME)

    # Chargement de la liste d'entrée
    try:
        with open(INPUT_FILE_PATH, "r", encoding="utf-8") as f:
            plants_list = json.load(f)
    except FileNotFoundError:
        print(f"⛔ ERREUR : Le fichier {INPUT_FILE_PATH} est introuvable.")
        return
    except json.JSONDecodeError:
        print(f"⛔ ERREUR : Le fichier {INPUT_FILE_PATH} n'est pas un JSON valide.")
        return

    print(f"🚀 Démarrage : {len(plants_list)} plantes à traiter.")
    print(f"📁 Sortie vers : {OUTPUT_FOLDER}/")

    # Boucle sur chaque plante
    for plant in plants_list:
        process_one_plant(plant, model)
        # Petite pause pour respecter les limites de l'API (Rate Limit)
        time.sleep(4)

    print("\n🏁 Terminé.")

if __name__ == "__main__":
    main()