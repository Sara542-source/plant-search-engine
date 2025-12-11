import json
import os

# --- CONFIGURATION ---
# 1. Nom de ton fichier Agriculture (celui avec "arrosage", "irrigation"...)
FICHIER_AGRI = r'docs\Thesaurus\Thesaurus_concepts.json' 

# 2. Nom de ton fichier Plantes converti (celui que tu viens de créer)
FICHIER_PLANTES = r'docs\Thesaurus\thesaurus_plantes_converti.json'
# 3. Nom du fichier final qui sera utilisé par ton SRI
FICHIER_FINAL = r'docs\Thesaurus\thesaurus_complet.json'

def fusionner_jsons():
    # --- ETAPE 1 : Chargement des fichiers ---
    try:
        print(f"1. Lecture de {FICHIER_AGRI}...")
        with open(FICHIER_AGRI, 'r', encoding='utf-8') as f1:
            data_agri = json.load(f1)
            
        print(f"2. Lecture de {FICHIER_PLANTES}...")
        with open(FICHIER_PLANTES, 'r', encoding='utf-8') as f2:
            data_plantes = json.load(f2)
            
    except FileNotFoundError as e:
        print(f"ERREUR CRITIQUE : Un fichier est manquant.\nDétail : {e}")
        return
    except json.JSONDecodeError:
        print("ERREUR : L'un des fichiers contient une erreur de syntaxe JSON.")
        return

    # --- ETAPE 2 : La Fusion ---
    # On commence avec les données d'agriculture comme base
    thesaurus_merge = data_agri.copy()
    
    conflits = 0
    
    print("3. Fusion en cours...")
    
    # On ajoute les plantes une par une
    for cle, valeur in data_plantes.items():
        # Petite vérification de sécurité : est-ce que le mot existe déjà ?
        if cle in thesaurus_merge:
            print(f"   ATTENTION : Le terme '{cle}' existe dans les deux fichiers ! La version 'Plantes' va écraser l'autre.")
            conflits += 1
        
        # Ajout / Écrasement
        thesaurus_merge[cle] = valeur

    # --- ETAPE 3 : Sauvegarde ---
    print(f"4. Sauvegarde dans {FICHIER_FINAL}...")
    with open(FICHIER_FINAL, 'w', encoding='utf-8') as f_out:
        json.dump(thesaurus_merge, f_out, indent=2, ensure_ascii=False)

    # --- RAPPORT FINAL ---
    print("-" * 30)
    print("FUSION TERMINÉE AVEC SUCCÈS !")
    print(f"- Concepts Agriculture : {len(data_agri)}")
    print(f"- Concepts Plantes     : {len(data_plantes)}")
    print(f"- TOTAL DANS LE FINAL  : {len(thesaurus_merge)}")
    
    if conflits > 0:
        print(f"- Nombre de doublons écrasés : {conflits}")
    else:
        print("- Aucun conflit détecté.")

if __name__ == "__main__":
    fusionner_jsons()