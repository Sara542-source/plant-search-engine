import json
import math
import os

INVERTED_PATH = r"C:\Users\sara slimani\Projets_dev\plant_search\inverted_index_git.json"
OUTPUT_PATH = "tfidf_scores.json"

# Charger l’inverted index
with open(INVERTED_PATH, "r", encoding="utf-8") as f:
    inverted = json.load(f)

# Extraire la liste de tous les documents
all_docs = set()
for word, posting in inverted.items():
    all_docs.update(posting.keys())

N = len(all_docs)  # nombre total de documents

# Structure : {doc_id: tfidf_total}
tfidf_scores = {doc: 0.0 for doc in all_docs}

for word, posting in inverted.items():

    df = len(posting)  # nombre de documents contenant ce mot
    if df == 0:
        continue

    idf = math.log(N / df)

    for doc_id, tf in posting.items():
        tfidf_scores[doc_id] += tf * idf

# Sauvegarder
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(tfidf_scores, f, indent=4, ensure_ascii=False)

print("TF-IDF généré dans :", OUTPUT_PATH)
