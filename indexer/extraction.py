import json
import os
import re
import pdfplumber

# --- CONFIGURATION ---
DOSSIER_JSON = "./docs/Plantes"
DOSSIER_PDF = "./docs/Concepts"
FICHIER_SORTIE = "SCientific.json"
FICHIER_DICO_LOCAL = r"C:\Users\USER\PycharmProjects\plant-search-engine\docs\fr.txt"

vip_list = set()
mots_a_garder = set()
dictionnaire_francais = set()

# Liste de suffixes français typiques (Sécurité supplémentaire)
SUFFIXES_BANNIS = (
    "euse", "euses", "eux", "ées", "âtre", "âtres", "ante", "antes", "ement",
    "age", "tion", "sion", "isme", "iste", "ance", "ence", "ité", "eur", "able",
    "ible", "if", "ive", "al", "ale", "aux", "et", "ette", "in", "ine", "on", "onne"
)

# Regex pour détecter les noms scientifiques complets
# Exemple : "Genus species" ou "Genus species var. something"
REGEX_LATIN = re.compile(r'\b[A-Z][a-z]+ [a-z]+(?: var\. [a-z]+)?\b')


def charger_dictionnaire_local():
    mots = set()
    if not os.path.exists(FICHIER_DICO_LOCAL):
        print(f"❌ ERREUR : Le fichier '{FICHIER_DICO_LOCAL}' est introuvable !")
        return set()

    print("📚 Chargement du dictionnaire local...")
    try:
        with open(FICHIER_DICO_LOCAL, "r", encoding="utf-8") as f:
            for line in f:
                mot = line.strip().lower()
                if mot:
                    mots.add(mot)
        # Ajout manuel de sécurité
        mots.update(["tubulé", "tubulée", "tubulées", "tubuleux", "tubéreux", "lancéolé", "lancéolée"])
        # Retirer certaines terminaisons latines si présentes
        for t in ["us", "um", "ii", "ae", "a"]:
            if t in mots:
                mots.remove(t)
        print(f"✅ Dictionnaire chargé : {len(mots)} mots.")
        return mots
    except Exception as e:
        print(f"❌ Erreur de lecture : {e}")
        return set()


def nettoyer_str(texte):
    if isinstance(texte, str):
        return texte.replace("_", " ").replace("-", " ").strip()
    return ""


def extraire_texte_json_recursif(data):
    texte_accumule = ""
    if isinstance(data, dict):
        for k, v in data.items():
            if k in ["galerie_images", "urls", "id", "image", "images", "slug"]:
                continue
            texte_accumule += " " + extraire_texte_json_recursif(v)
    elif isinstance(data, list):
        for item in data:
            texte_accumule += " " + extraire_texte_json_recursif(item)
    elif isinstance(data, str):
        texte_accumule += " " + nettoyer_str(data)
    return texte_accumule


# =========================================================
# INITIALISATION
# =========================================================
dictionnaire_francais = charger_dictionnaire_local()
if not dictionnaire_francais:
    exit()

# =========================================================
# ÉTAPE 1 : VIP LIST (JSON)
# =========================================================
print("🛡️  Étape 1 : VIP List...")
if os.path.exists(DOSSIER_JSON):
    for filename in os.listdir(DOSSIER_JSON):
        if filename.endswith(".json"):
            try:
                with open(os.path.join(DOSSIER_JSON, filename), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    infos = data.get("infos_generales", {})

                    # Champs à garder : Scientifique, Famille, Genre, Darija
                    champs = [infos.get("nom_scientifique"), infos.get("famille"), infos.get("genre")]
                    for val in champs:
                        if val:
                            clean = nettoyer_str(val)
                            # ✅ Version complète
                            vip_list.add(clean)
                            # ✅ Version décomposée pour recherche flexible
                            for m in clean.split():
                                vip_list.add(m)

                    # Darija
                    for nom in infos.get("noms_darija", []):
                        clean = nettoyer_str(nom)
                        vip_list.add(clean)
                        for m in clean.split():
                            vip_list.add(m)

            except Exception as e:
                print(f"❌ Erreur lecture JSON {filename}: {e}")
                pass

# =========================================================
# ÉTAPE 2 : EXTRACTION
# =========================================================
print("🚜 Étape 2 : Extraction du texte...")
texte_vrac = ""

# JSON
if os.path.exists(DOSSIER_JSON):
    for filename in os.listdir(DOSSIER_JSON):
        if filename.endswith(".json"):
            with open(os.path.join(DOSSIER_JSON, filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
                texte_vrac += extraire_texte_json_recursif(data) + " "

# PDF
if os.path.exists(DOSSIER_PDF):
    pdf_files = [f for f in os.listdir(DOSSIER_PDF) if f.endswith(".pdf")]
    for filename in pdf_files:
        try:
            with pdfplumber.open(os.path.join(DOSSIER_PDF, filename)) as pdf:
                for page in pdf.pages:
                    extract = page.extract_text()
                    if extract:
                        texte_vrac += nettoyer_str(extract) + " "
        except Exception as e:
            print(f"❌ Erreur lecture PDF {filename}: {e}")
            pass

# =========================================================
# ÉTAPE 3 : FILTRAGE TOTAL
# =========================================================
print("🧹 Étape 3 : Filtrage...")

mots_candidats = re.findall(r"[\w\u0600-\u06FF]+", texte_vrac)

for mot in mots_candidats:
    mot = mot.strip()
    mot_lower = mot.lower()

    # 1. VIP (Priorité absolue)
    if mot in vip_list:
        mots_a_garder.add(mot)
        continue

    # 2. Arabe/Darija
    if any("\u0600" <= c <= "\u06FF" for c in mot):
        mots_a_garder.add(mot)
        continue

    # 3. Nombres ou trop courts
    if re.search(r'\d', mot): continue
    if len(mot) < 3: continue

    # 4. Latin detection avec regex scientifique
    if REGEX_LATIN.match(mot):
        mots_a_garder.add(mot)
        continue

    # 5. Dictionnaire français
    if mot_lower in dictionnaire_francais: continue

    # 6. Suffixes français
    if mot_lower.endswith(SUFFIXES_BANNIS): continue

    # Si on survit à tout ça -> mot rare (latin/darija)
    mots_a_garder.add(mot)

# =========================================================
# SAUVEGARDE
# =========================================================
liste_finale = sorted(list(mots_a_garder))

with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
    json.dump(liste_finale, f, indent=2, ensure_ascii=False)

print("-" * 30)
print(f"✅ Terminé ! Fichier : {FICHIER_SORTIE}")
print(f"📊 {len(liste_finale)} mots conservés.")
