import json
import nltk
import re
from nltk.corpus import stopwords
from nltk.stem.snowball import FrenchStemmer
import os
from tqdm import tqdm

# Téléchargements NLTK
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')

stemmer = FrenchStemmer()
stop_fr = set(stopwords.words("french"))

###########################################################
# NORMALISATION
###########################################################
def normalize_text(text, protected_words=None):
    if not isinstance(text, str):
        return []

    if protected_words is None:
        protected_words = set()

    text = text.lower()

    text = re.sub(r"[^a-zàâçéèêëîïôûùüÿñæœ0-9\s]", " ", text)

    tokens = nltk.word_tokenize(text, language="french")

    cleaned = []

    for t in tokens:
        if t in protected_words:
            cleaned.append(t)
            continue

        if t in stop_fr:
            continue

        cleaned.append(stemmer.stem(t))

    return cleaned


###########################################################
# EXTRACTION DES TEXTES DANS LE JSON
###########################################################
def extract_text_fields(obj, ignore_keys=None):

    if ignore_keys is None:
        ignore_keys = set()

    texts = []

    if isinstance(obj, dict):
        for k, v in obj.items():

            if k in ignore_keys:
                continue

            if isinstance(v, str) and v.startswith("http"):
                continue

            if isinstance(v, str):
                texts.append(v)
            else:
                texts.extend(extract_text_fields(v, ignore_keys))

    elif isinstance(obj, list):
        for item in obj:
            texts.extend(extract_text_fields(item, ignore_keys))

    return texts


###########################################################
# INVERTED INDEX LOCAL
###########################################################
def build_inverted_index(tokens, doc_id):

    index = {}

    for t in tokens:
        if t not in index:
            index[t] = {}

        if doc_id not in index[t]:
            index[t][doc_id] = 0

        index[t][doc_id] += 1

    return index


###########################################################
# MERGE INVERTED INDEX
###########################################################
def merge_indexes(global_index, local_index):

    for token, posting in local_index.items():

        if token not in global_index:
            global_index[token] = posting
            continue

        for doc_id, count in posting.items():
            if doc_id not in global_index[token]:
                global_index[token][doc_id] = count
            else:
                global_index[token][doc_id] += count

    return global_index


###########################################################
# INDEXATION DE TOUS LES DOCUMENTS
###########################################################
DATA_DIR = "C:/Users/sara slimani/Projets_dev/plant_search/data"

def index_all_documents():
    global_index = {}

    for filename in tqdm(os.listdir(DATA_DIR)):

        if not filename.endswith(".json"):
            continue

        path = os.path.join(DATA_DIR, filename)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        except:
            print("Erreur JSON :", filename)
            continue

        ######################################################
        # GESTION DE 3 FORMATS POSSIBLES :
        #   {…}
        #   [{…}]
        #   [{…}, {…}]
        ######################################################

        if isinstance(data, dict):
            docs = [data]

        elif isinstance(data, list):
            docs = data

        else:
            print("Format inconnu :", filename)
            continue

        ######################################################
        # INDEXER CHAQUE DOCUMENT SEPARÉMENT
        ######################################################

        for i, plant in enumerate(docs):

            doc_id = f"{os.path.splitext(filename)[0]}_{i}"

            # Mots protégés : nom scientifique + darija
            protected = set()
            info = plant.get("infos_generales", {})

            if isinstance(info, dict):
                sci = info.get("nom_scientifique")
                if isinstance(sci, str):
                    protected.update(sci.lower().split())

                darija = info.get("noms_darija", [])
                if isinstance(darija, list):
                    protected.update([w.lower() for w in darija])

            # Extraction de tout le texte
            text_fields = extract_text_fields(
                plant,
                ignore_keys={"galerie_images", "urls"}
            )

            # Normalisation
            tokens = []
            for txt in text_fields:
                tokens.extend(normalize_text(txt, protected))

            # Index local
            local_index = build_inverted_index(tokens, doc_id)

            # Merge dans global
            merge_indexes(global_index, local_index)

    return global_index


###########################################################
# MAIN
###########################################################
if __name__ == "__main__":
    index = index_all_documents()

    with open("inverted_index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print("Index final :", len(index), "tokens indexés.")
