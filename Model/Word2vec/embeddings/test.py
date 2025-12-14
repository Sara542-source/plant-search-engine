import json
import numpy as np
from gensim.models import Word2Vec
from numpy.linalg import norm
import os
import sys
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "indexer")
    )
)

from preprocess import normalize_text

############################################
# Charger les données
############################################


def load_doc_vectors(path="doc_vectors.npy"):
    # np.load charge un dictionnaire Python si allow_pickle=True
    return np.load(path, allow_pickle=True).item()

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

############################################
# Similarité cosine
############################################

def cosine_sim(a, b):
    if norm(a) == 0 or norm(b) == 0:
        return 0
    return np.dot(a, b) / (norm(a) * norm(b))

############################################
# Recherche sémantique
############################################

def semantic_search(query, model, doc_vectors, tfidf_scores, top_k=10):
    # 1. Tokenisation
    tokens = normalize_text(query, protected_words=set())

    # 2. Vecteur moyen de la requête
    vectors = [model.wv[w] for w in tokens if w in model.wv]
    if not vectors:
        print("Aucun mot de la requête n’est dans le modèle.")
        return []

    query_vec = np.mean(vectors, axis=0)

    # 3. Similarité sémantique
    semantic_scores = {
        doc_id: cosine_sim(query_vec, vec)
        for doc_id, vec in doc_vectors.items()
    }

    # 4. Combinaison avec TF-IDF
    final_scores = {}
    for doc_id, sem_score in semantic_scores.items():
        tfidf = tfidf_scores.get(doc_id, 0)
        final_scores[doc_id] = 0.6 * sem_score + 0.4 * tfidf

    # 5. Ranking
    ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)

    return ranked[:top_k]

############################################
# MAIN test
############################################

if __name__ == "__main__":
    print("Chargement du modèle...")
    model = Word2Vec.load("word2vec.model")

    print("Chargement des vecteurs documents...")
    doc_vectors = load_doc_vectors("doc_vectors.npy")

    print("Chargement TF-IDF...")
    tfidf_scores = load_json("tfidf_scores.json")

    # Entrée utilisateur
    q = input("Entrez votre requête : ")

    results = semantic_search(q, model, doc_vectors, tfidf_scores)

    print("\nRésultats :")
    for doc_id, score in results:
        print(f"- Document {doc_id} | score={score:.4f}")
