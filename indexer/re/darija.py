import json
import os
import time
import re
import google.generativeai as genai
from google.api_core import exceptions

# --- CONFIGURATION ---
API_KEY = ""  # ⚠️ Remets ta clé ici
INPUT_FILE = r'C:\Users\USER\PycharmProjects\plant-search-engine\docs\Thesaurus\thesaurus_plantes.json'
OUTPUT_FILE = 'thesaurus_botanique_enriched.json'

# Configuration
genai.configure(api_key=API_KEY)

# ⚠️ CORRECTION IMPORTANTE : Utilise explicitement 'gemini-1.5-flash'
# 'gemini-2.5' ou les versions expérimentales ont des quotas très faibles (20/jour).
# La 1.5 Flash permet ~15 requêtes/minute et 1500/jour.
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={"response_mime_type": "application/json"}
)

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def extract_wait_time(error_message):
    """
    Extrait le temps d'attente demandé par Google depuis le message d'erreur.
    Cherche "retry in X s" ou "retry_delay { seconds: X }"
    """
    # Pattern 1: "Please retry in 45.5s"
    match = re.search(r"retry in (\d+(\.\d+)?)s", str(error_message))
    if match:
        return float(match.group(1)) + 2 # On ajoute 2 secondes de sécurité
    
    # Pattern 2: "seconds: 45" (format protobuf dans ton log)
    match = re.search(r"seconds:\s*(\d+)", str(error_message))
    if match:
        return int(match.group(1)) + 2
        
    return 60 # Par défaut, si on ne trouve pas, on attend 1 minute

def generate_darija_variations_safe(plant_name, current_labels):
    """
    Version robuste qui attend si l'API est surchargée.
    """
    prompt = f"""
    Tu es un expert botanique marocain.
    Tâche : Pour la plante "{plant_name}", génère une liste JSON de synonymes en Darija (Arabizi et Arabe) et variations phonétiques.
    Basé sur : {current_labels}
    Output attendu : ["variante1", "variante2"] (JSON STRICT)
    """
    
    max_retries = 5
    attempt = 0
    
    while attempt < max_retries:
        try:
            response = model.generate_content(prompt)
            # Nettoyage JSON
            text_resp = response.text.replace('```json', '').replace('```', '')
            variations = json.loads(text_resp)
            
            cleaned = [v.strip().lower() for v in variations if isinstance(v, str)]
            return cleaned

        except exceptions.ResourceExhausted as e:
            # C'est ici qu'on gère l'erreur 429
            wait_seconds = extract_wait_time(e)
            print(f"   ⏳ Quota dépassé. Pause imposée de {wait_seconds:.1f} secondes...")
            time.sleep(wait_seconds)
            attempt += 1
            
        except Exception as e:
            print(f"   ⚠️ Erreur autre ({e}). Essai {attempt+1}/{max_retries}")
            time.sleep(5)
            attempt += 1

    print(f"   ❌ Abandon pour {plant_name} après {max_retries} tentatives.")
    return []

def main():
    print("🚀 Démarrage de l'enrichissement (Mode Safe)...")
    
    if os.path.exists(OUTPUT_FILE):
        print("📂 Reprise du fichier existant...")
        thesaurus = load_json(OUTPUT_FILE)
    else:
        thesaurus = load_json(INPUT_FILE)

    if not thesaurus: return

    # Calculer combien il en reste à faire pour afficher une barre de progression correcte
    plant_items = list(thesaurus.items())
    total_plants = len(plant_items)
    
    modified_count = 0

    for index, (plant_id, data) in enumerate(plant_items):
        plant_name = data.get('prefLabel')
        current_alts = data.get('altLabels', [])
        
        # Astuce : Si la plante a déjà beaucoup d'altLabels (ex > 5), on suppose qu'elle est déjà traitée
        # Cela permet de relancer le script sans refaire celles qui sont déjà faites
        # Tu peux commenter cette ligne si tu veux forcer le retraitement
        if len(current_alts) > 5 and "enriched" in data.get('flags', []): 
            continue

        print(f"[{index+1}/{total_plants}] Traitement : {plant_name}...")

        new_variations = generate_darija_variations_safe(plant_name, current_alts)
        
        if new_variations:
            existing_set = set(current_alts)
            original_len = len(existing_set)
            existing_set.update(new_variations)
            
            data['altLabels'] = list(existing_set)
            # On ajoute un flag pour savoir que cette plante est faite
            if 'flags' not in data: data['flags'] = []
            if "enriched" not in data['flags']: data['flags'].append("enriched")
            
            added = len(existing_set) - original_len
            if added > 0:
                print(f"   ✅ +{added} ajouts.")
                modified_count += 1
            
            # Sauvegarde régulière
            save_json(thesaurus, OUTPUT_FILE)

        # Petite pause standard entre les succès pour éviter de taper le mur trop vite
        time.sleep(5) 

    print("-" * 30)
    print(f"🎉 Terminé ! {modified_count} plantes mises à jour.")

if __name__ == "__main__":
    main()