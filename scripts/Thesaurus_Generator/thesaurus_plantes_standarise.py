import json

# --- CONFIGURATION ---
# Mets ici le nom exact de ton fichier qui contient les 95 plantes
FICHIER_ENTREE = r'docs\Thesaurus\thesaurus_plantes.json' 
FICHIER_SORTIE = r'docs\Thesaurus\thesaurus_plantes_converti.json'

try:
    # 1. Lire ton fichier complet
    print(f"Lecture du fichier : {FICHIER_ENTREE} ...")
    with open(FICHIER_ENTREE, 'r', encoding='utf-8') as f:
        data_plantes = json.load(f)

    # 2. Préparer le dictionnaire vide pour le résultat
    thesaurus_final = {}

    # 3. Boucle sur TOUTES les entrées de ton fichier
    for plante, details in data_plantes.items():
        
        # Transformation vers le format standard
        nouvel_objet = {
            "BT": details.get("broader", []),         # Famille / Genre
            "NT": [],                                 # Vide par défaut
            # Fusion de related et flags dans RT
            "RT": details.get("related", []) + details.get("flags", []),
            "UF": details.get("altLabels", [])        # Synonymes + Arabe
        }

        # Ajout dans le nouveau dictionnaire
        thesaurus_final[plante] = nouvel_objet

    # 4. Sauvegarder le résultat
    print(f"Transformation de {len(thesaurus_final)} plantes en cours...")
    
    with open(FICHIER_SORTIE, 'w', encoding='utf-8') as f_out:
        json.dump(thesaurus_final, f_out, indent=2, ensure_ascii=False)

    print("-" * 30)
    print("TERMINE !")
    print(f"Le fichier '{FICHIER_SORTIE}' a été créé avec succès.")
    print("Tu peux maintenant le fusionner avec ton fichier agriculture.")

except FileNotFoundError:
    print(f"ERREUR : Le fichier '{FICHIER_ENTREE}' n'a pas été trouvé.")
    print("Vérifie que le nom est correct et qu'il est dans le même dossier.")
except json.JSONDecodeError:
    print(f"ERREUR : Ton fichier '{FICHIER_ENTREE}' contient une erreur de syntaxe JSON.")