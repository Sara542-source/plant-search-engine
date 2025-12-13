from sklearn.metrics.pairwise import cosine_similarity
from preprocess_query import preprocess_query
from charger_stock_scientifique import charger_stock_scientifique
import numpy as np
import json
def lsa_search(query: str):
    # 1. Load Pre-computed Data
    document_concepts = np.load("lsa_document_concepts.npy")
    U_k = np.load("lsa_U_k.npy")
    sigma_k = np.load("lsa_sigma_k.npy")
    global_weights = np.load("lsa_global_weights.npy")
    
    with open("lsa_metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    all_terms = meta["all_terms"]
    all_documents = meta["all_documents"]
    term_to_index = {term: i for i, term in enumerate(all_terms)}

    # 2. Setup Resources
    FICHIER_STOCK_SCIENTIFIQUE = "../../../docs/mot_scientifique/protected_terms.json"
    FICHIER_STOCK_TECHNIQUE = "../../../docs/mot_technique/protected_concepts.json"
    TERMES_SCIENTIFIQUES_STOCK = charger_stock_scientifique(FICHIER_STOCK_SCIENTIFIQUE) 
    TERMES_TECHNIQUES_STOCK = charger_stock_scientifique(FICHIER_STOCK_TECHNIQUE)
    
    # 3. Process Query
    processed_query = preprocess_query(query, TERMES_SCIENTIFIQUES_STOCK | TERMES_TECHNIQUES_STOCK, 4)
    
    # 4. Create Query Vector
    q_vector = np.zeros(len(all_terms))
    scientific_boost = 5
    technical_boost = 1.2

    for token in processed_query:
        if token in term_to_index:
            idx = term_to_index[token]
            weight = (1 + np.log(1)) * global_weights[idx]
            
            if token in TERMES_SCIENTIFIQUES_STOCK:
                weight *= scientific_boost
            elif token in TERMES_TECHNIQUES_STOCK:
                weight *= technical_boost
            
            q_vector[idx] = weight

    # 5. Fold-in: Project query into the LSA space
    sigma_inv = np.diag(1 / sigma_k)
    q_concept = q_vector @ U_k @ sigma_inv 

    # 6. Similarity Calculation
    similarities = cosine_similarity(q_concept.reshape(1, -1), document_concepts)
    top_idx = np.argsort(similarities[0])[::-1][:30] 
    
    return [all_documents[idx] for idx in top_idx]

r=lsa_search("Je veux semer Petroselinum crispum avec arrosage modéré")
for i in range (0,30) :
        print(f"{i+1}. Document: {r[i]}")