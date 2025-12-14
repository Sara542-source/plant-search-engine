import json
import os
import sys
import numpy as np
from tqdm import tqdm
from gensim.models import Word2Vec
from numpy.linalg import norm

# Import preprocess
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "indexer")))
from preprocess import normalize_text, extract_text_fields, DATA_DIR

#####################################################################
# 1. Construire le corpus Word2Vec
#####################################################################

def load_corpus():
    corpus = []

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

        docs = data if isinstance(data, list) else [data]

        for plant in docs:
            info = plant.get("infos_generales", {})
            protected = set()

            if isinstance(info, dict):
                sci = info.get("nom_scientifique")
                if isinstance(sci, str):
                    protected.update(sci.lower().split())

                darija = info.get("noms_darija", [])
                if isinstance(darija, list):
                    protected.update([w.lower() for w in darija])

            fields = extract_text_fields(
                plant,
                ignore_keys={"galerie_images", "urls"}
            )

            for ftxt in fields:
                tokens = normalize_text(ftxt, protected)

                if len(tokens) > 2:
                    corpus.append(tokens)

    return corpus


#####################################################################
# 2. Entraîner Word2Vec
#####################################################################

def train_word2vec():
    print("Chargement du corpus...")
    corpus = load_corpus()

    model = Word2Vec(
        sentences=corpus,
        vector_size=100,
        window=5,
        min_count=1,
        workers=4,
        sg=1
    )

    model.save("word2vec.model")
    print("Modèle Word2Vec enregistré dans word2vec.model")


#####################################################################
# 3. Convertir chaque document JSON en vecteur
#####################################################################

def get_document_vector(model, text_fields, protected, scientific_tokens=None, boost=2.0):
    """
    Convertit un document en vecteur Word2Vec.
    
    - model : modèle Word2Vec entraîné
    - text_fields : liste de textes du document
    - protected : mots à protéger du stemming
    - scientific_tokens : set de mots scientifiques du document
    - boost : facteur de pondération pour les mots scientifiques
    """
    all_tokens = []

    for ftxt in text_fields:
        tokens = normalize_text(ftxt, protected)
        all_tokens.extend(tokens)

    vectors = []
    for word in all_tokens:
        if word in model.wv:
            vec = model.wv[word]
            if scientific_tokens and word in scientific_tokens:
                vec = vec * boost  # pondération des mots scientifiques
            vectors.append(vec)

    if not vectors:
        return np.zeros(model.vector_size)

    return np.mean(vectors, axis=0)


def index_documents(model):
    doc_vectors = {}        # {doc_id: vecteur_numpy}

    for filename in tqdm(os.listdir(DATA_DIR)):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(DATA_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        docs = data if isinstance(data, list) else [data]

        for plant in docs:
            doc_id = plant.get("id") or plant.get("_id") or filename

            info = plant.get("infos_generales", {})
            protected = set()

            if isinstance(info, dict):
                sci = info.get("nom_scientifique")
                if isinstance(sci, str):
                    protected.update(sci.lower().split())

                darija = info.get("noms_darija", [])
                if isinstance(darija, list):
                    protected.update([w.lower() for w in darija])

            text_fields = extract_text_fields(
                plant,
                ignore_keys={"galerie_images", "urls"}
            )

            doc_vec = get_document_vector(model, text_fields, protected)
            doc_vectors[doc_id] = doc_vec

    np.save("doc_vectors.npy", doc_vectors)
    print("Vecteurs documents enregistrés dans doc_vectors.npy")


#####################################################################
# 4. Similarité cosine
#####################################################################

def cosine_sim(a, b):
    if norm(a) == 0 or norm(b) == 0:
        return 0
    return np.dot(a, b) / (norm(a) * norm(b))


#####################################################################
# 5. Recherche utilisateur : Word2Vec + TF-IDF
#####################################################################

def semantic_search(query, model, doc_vectors, inverted_index, tfidf_scores):
    tokens = normalize_text(query, protected=set())
    query_vec = np.mean([model.wv[w] for w in tokens if w in model.wv], axis=0)

    semantic_scores = {}
    for doc_id, vec in doc_vectors.items():
        semantic_scores[doc_id] = cosine_sim(query_vec, vec)

    final_scores = {}
    for doc_id in semantic_scores:
        tfidf = tfidf_scores.get(doc_id, 0)
        sem = semantic_scores[doc_id]

        final_scores[doc_id] = 0.6 * sem + 0.4 * tfidf

    ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked




#####################################################################
# MAIN
#####################################################################

if __name__ == "__main__":
    train_word2vec()

    model = Word2Vec.load("word2vec.model")

    index_documents(model)

    print("Tout est prêt. Le modèle + index vectoriel est généré.")
