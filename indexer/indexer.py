import os
import json
import re
import unicodedata
from collections import defaultdict
from pypdf import PdfReader

# Importation de votre config mise à jour
# Assurez-vous que config.py est bien dans le dossier 'indexer'
from config import get_stop_words, INDEX_OUTPUT_PATH, DATA_DIR_JSON, DATA_DIR_PDF


class Indexer:
    def __init__(self):
        # Index inversé global
        self.index = defaultdict(dict)
        # Métadonnées pour l'affichage (Titre, Image, Résumé)
        self.metadata = {}
        # Stop words chargés depuis config.py
        self.stop_words = get_stop_words()

        # Utilisation de VOS variables définies dans config.py
        self.json_folder = DATA_DIR_JSON  # ../docs/Plantes
        self.pdf_folder = DATA_DIR_PDF  # ../docs/Concepts

    def retirer_accents(self, texte):
        """Nettoie les accents pour la normalisation (été -> ete)"""
        try:
            texte = unicodedata.normalize('NFD', texte)
            texte = "".join([c for c in texte if unicodedata.category(c) != 'Mn'])
            return texte
        except Exception:
            return texte

    def nettoyer_texte(self, texte, is_scientific=False):
        """
        Tokenisation et nettoyage adapté au contexte.
        is_scientific=True protège les noms latins.
        """
        if not texte:
            return []

        texte = texte.lower()

        # CAS 1 : Nom Scientifique (Latin)
        if is_scientific:
            # On garde les tirets pour le latin (ex: Mentha x piperita)
            texte = re.sub(r'[^a-z0-9\-]+', ' ', texte)
            return texte.strip().split()

        # CAS 2 : Texte Général (Français / Darija)
        texte = self.retirer_accents(texte)

        # Gestion des mots composés : on remplace tiret par espace
        # "anti-inflammatoire" -> "anti inflammatoire" (plus facile à trouver)
        texte = texte.replace('-', ' ').replace('_', ' ')

        # On ne garde que les lettres et les chiffres
        texte = re.sub(r'[^a-z0-9]+', ' ', texte)

        mots = texte.split()

        # Filtrage (Stop words) et Stemming léger
        mots_propres = []
        for mot in mots:
            if mot not in self.stop_words and len(mot) > 1:
                # Petite astuce : on enlève le 's' final du pluriel si le mot est long
                if mot.endswith('s') and len(mot) > 3:
                    mots_propres.append(mot[:-1])
                else:
                    mots_propres.append(mot)

        return mots_propres

    def ajouter_au_dict(self, tokens, doc_id):
        """Ajoute les tokens nettoyés à l'index inversé"""
        for mot in tokens:
            if doc_id in self.index[mot]:
                self.index[mot][doc_id] += 1
            else:
                self.index[mot][doc_id] = 1

    def extraire_texte_recursif(self, structure):
        """
        Extrait le texte de n'importe quelle structure JSON imbriquée
        (sections, children, listes, dicts...)
        """
        texte_accumule = ""

        if isinstance(structure, list):
            for element in structure:
                texte_accumule += self.extraire_texte_recursif(element)

        elif isinstance(structure, dict):
            # On prend le titre et le contenu de la section actuelle
            texte_accumule += structure.get('title', '') + " "
            texte_accumule += structure.get('content', '') + " "

            # On descend récursivement dans les sous-sections
            if 'sections' in structure:
                texte_accumule += self.extraire_texte_recursif(structure['sections'])
            if 'children' in structure:
                texte_accumule += self.extraire_texte_recursif(structure['children'])

        return texte_accumule

    def indexer_json(self):
        """Traitement des plantes (JSON)"""
        print(f"\n📂 Indexation JSON depuis : {self.json_folder}")

        if not os.path.exists(self.json_folder):
            print(f"❌ Erreur : Dossier introuvable {self.json_folder}")
            return

        count = 0
        for filename in os.listdir(self.json_folder):
            if filename.endswith(".json"):
                filepath = os.path.join(self.json_folder, filename)
                doc_id = filename

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        infos = data.get('infos_generales', {})

                        # --- 1. MÉTADONNÉES (Pour l'affichage) ---
                        self.metadata[doc_id] = {
                            "titre": infos.get('nom_commun', 'Plante'),
                            "sous_titre": infos.get('nom_scientifique', ''),
                            # On prend la première image ou None
                            "image": data.get('galerie_images', [None])[0],
                            # On prend un bout du résumé pour l'aperçu
                            "resume": data.get('source_data', {}).get('resume', '')[:250] + "...",
                            "type": "plante"
                        }

                        # --- 2. CONSTRUCTION DU TEXTE À INDEXER ---
                        contenu = f"{infos.get('nom_commun', '')} {infos.get('nom_scientifique', '')} "
                        contenu += " ".join(infos.get('noms_darija', [])) + " "
                        contenu += " ".join(infos.get('noms_alternatifs', [])) + " "

                        # Attributs spécifiques (dynamiques)
                        attrs = data.get('attributs_specifiques', {})
                        for k, v in attrs.items(): contenu += f"{k} {v} "

                        # Caractéristiques
                        caracs = data.get('caracteristiques', {})
                        contenu += f"{caracs.get('arrosage', '')} {caracs.get('type_sol', '')} "

                        # Utilisations
                        usages = data.get('utilisations', {})
                        for cat, liste in usages.items(): contenu += " ".join(liste) + " "

                        # Texte complet récursif
                        source = data.get('source_data', {})
                        contenu += source.get('resume', '') + " "
                        full_text = source.get('texte_complet', {})
                        contenu += full_text.get('introduction', '') + " "
                        contenu += self.extraire_texte_recursif(full_text.get('sections', []))

                        # --- 3. INDEXATION ---
                        # Nom Scientifique (Mode protégé)
                        tokens_science = self.nettoyer_texte(infos.get('nom_scientifique', ''), is_scientific=True)
                        self.ajouter_au_dict(tokens_science, doc_id)

                        # Reste du texte (Mode normal)
                        tokens_texte = self.nettoyer_texte(contenu, is_scientific=False)
                        self.ajouter_au_dict(tokens_texte, doc_id)

                        count += 1

                except Exception as e:
                    print(f"⚠️ Erreur JSON {filename}: {e}")
        print(f"✅ {count} plantes indexées.")

    def indexer_pdf(self):
        """Traitement des concepts (PDF Texte Simple)"""
        print(f"\n📂 Indexation PDF depuis : {self.pdf_folder}")

        if not os.path.exists(self.pdf_folder):
            print(f"❌ Erreur : Dossier introuvable {self.pdf_folder}")
            return

        count = 0
        for filename in os.listdir(self.pdf_folder):
            if filename.endswith(".pdf"):
                filepath = os.path.join(self.pdf_folder, filename)
                doc_id = filename

                try:
                    reader = PdfReader(filepath)
                    texte_complet = ""
                    # On aspire tout le texte
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            texte_complet += extracted + " "

                    # --- 1. MÉTADONNÉES PDF ---
                    # Titre propre basé sur le nom du fichier (Arrosage_plante.pdf -> Arrosage plante)
                    titre_propre = filename.replace('.pdf', '').replace('_', ' ').capitalize()

                    # Génération d'un résumé automatique (200 premiers caractères de la definition ou lintroduction)
                    # 1. On définit les mots-clés qui annoncent le début du contenu intéressant
                    # On met "définition" en premier car c'est le plus probable
                    mots_cles_debut = ["définition", "definition", "introduction", "généralités"]

                    resume_auto = ""
                    texte_lower = texte_complet.lower()

                    # 2. On cherche la position du premier mot-clé trouvé
                    index_trouve = -1
                    for mot in mots_cles_debut:
                        # On cherche le mot clé (ex: "définition")
                        index = texte_lower.find(mot)
                        if index != -1:
                            # Si trouvé, on se place juste après le mot (+ sa longueur)
                            index_trouve = index + len(mot)
                            break

                    # 3. Extraction du résumé
                    if index_trouve != -1:
                        # Cas A : On a trouvé "Définition"
                        # On prend les 300 caractères qui suivent
                        extrait = texte_complet[index_trouve: index_trouve + 300]

                        # Nettoyage : On enlève les deux points (:), les tirets ou les sauts de ligne au début
                        # Ex: "Définition : La botanique..." -> devient "La botanique..."
                        extrait = extrait.lstrip(" :.-\n\r\t")

                        resume_auto = extrait.replace('\n', ' ') + "..."
                    else:
                        # Cas B : Pas de mot "Définition", on prend le début du PDF (Fallback)
                        resume_auto = texte_complet[:250].replace('\n', ' ') + "..."
                    # Sécurité si le texte est vide
                    if not resume_auto.strip():
                            resume_auto = "Aperçu non disponible."
                    self.metadata[doc_id] = {
                        "titre": titre_propre,
                        "sous_titre": "Fiche Concept",
                        "image": None,  # EXPLICITEMENT None car pas de photo
                        "resume": resume_auto,
                        "type": "concept"
                    }

                    # --- 2. INDEXATION ---
                    tokens = self.nettoyer_texte(texte_complet, is_scientific=False)
                    self.ajouter_au_dict(tokens, doc_id)

                    count += 1
                    print(f"  - {filename} traité")

                except Exception as e:
                    print(f"⚠️ Erreur PDF {filename}: {e}")

        print(f"✅ {count} concepts PDF indexés.")

    def sauvegarder(self):
        """Sauvegarde finale"""
        print(f"\n💾 Sauvegarde vers {INDEX_OUTPUT_PATH}...")
        output_data = {"metadata": self.metadata, "index": self.index}

        try:
            with open(INDEX_OUTPUT_PATH, 'w', encoding='utf-8') as f:
                # indent=None réduit la taille du fichier (pas d'espaces inutiles)
                json.dump(output_data, f, ensure_ascii=False)
            print(f"🎉 SUCCÈS ! Index généré.")
            print(f"📊 Stats : {len(self.index)} mots uniques indexés.")
        except Exception as e:
            print(f"❌ Erreur sauvegarde : {e}")


if __name__ == "__main__":
    moteur = Indexer()
    moteur.indexer_json()
    moteur.indexer_pdf()
    moteur.sauvegarder()