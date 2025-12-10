import json
import os
import glob


def extract_protected_terms_from_directory(directory_path, output_file_path):
    # Ensemble pour stocker les mots uniques (évite les doublons globaux)
    protected_words = set()

    # 1. Récupérer la liste de tous les fichiers .json dans le dossier
    # os.path.join assure que le chemin est correct sur Windows et Linux
    json_files = glob.glob(os.path.join(directory_path, "*.json"))

    if not json_files:
        print(f"Aucun fichier JSON trouvé dans : {directory_path}")
        return []

    print(f"Traitement de {len(json_files)} fichiers trouvés...")

    # Champs à cibler
    simple_fields = ["nom_scientifique", "nom_commun", "famille", "genre"]
    list_fields = ["noms_darija"]

    # --- Fonction interne pour traiter un texte ---
    def process_text(text):
        if not text or not isinstance(text, str):
            return
        # Forme complète
        clean_text = text.strip()
        protected_words.add(clean_text)
        # Composants individuels
        parts = clean_text.split()
        if len(parts) > 1:
            for part in parts:
                protected_words.add(part)

    # 2. Boucle sur chaque fichier trouvé
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # On cible 'infos_generales'
                info = data.get("infos_generales", {})

                # Extraction
                for field in simple_fields:
                    process_text(info.get(field))

                for field in list_fields:
                    values = info.get(field, [])
                    for value in values:
                        process_text(value)

        except Exception as e:
            print(f"Erreur lors de la lecture du fichier {file_path}: {e}")

    # 3. Sauvegarde
    final_list = list(protected_words)
    final_list.sort()

    with open(output_file_path, 'w', encoding='utf-8') as f_out:
        json.dump(final_list, f_out, ensure_ascii=False, indent=2)

    print(f"SUCCÈS : {len(final_list)} termes protégés extraits et sauvegardés dans '{output_file_path}'")
    return final_list


# --- Configuration ---
# Met ici le chemin vers TON DOSSIER (celui qui a causé l'erreur)
input_directory = 'docs/Plantes'
output_json = 'protected_terms.json'

# Lancer l'extraction
if __name__ == "__main__":
    extract_protected_terms_from_directory(input_directory, output_json)