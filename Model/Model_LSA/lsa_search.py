import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from preprocess_query import preprocess_query
from charger_stock_scientifique import charger_stock_scientifique

# Load these once and reuse (put outside the function if using in a web app)
FICHIER_STOCK_SCIENTIFIQUE = "../../docs/mot_scientifique/protected_terms.json"
FICHIER_STOCK_TECHNIQUE = "../../docs/mot_technique/protected_concepts.json"
TERMES_SCIENTIFIQUES_STOCK = charger_stock_scientifique(FICHIER_STOCK_SCIENTIFIQUE) 
TERMES_TECHNIQUES_STOCK = charger_stock_scientifique(FICHIER_STOCK_TECHNIQUE)
MAX_NGRAM_SCIENTIFIQUE = 4

# Load the pre-built LSA model
with open('lsa_model.pkl', 'rb') as f:
    saved_model = pickle.load(f)

def lsa_search(query: str, top_n: int = 30):
    """
    Fast LSA search using pre-built model.
    This is the function to call for each query.
    """
    # Unpack saved model components
    term_to_index = saved_model['term_to_index']
    all_documents = saved_model['all_documents']
    global_weights = saved_model['global_weights']
    lsa = saved_model['lsa_model']
    document_concepts = saved_model['document_concepts']
    A_dense = saved_model['A_dense']
    num_terms = saved_model['num_terms']
    
    k = lsa.n_components
    
    # --- Preprocess query ---
    processed_query = preprocess_query(
        query, 
        TERMES_SCIENTIFIQUES_STOCK | TERMES_TECHNIQUES_STOCK, 
        MAX_NGRAM_SCIENTIFIQUE
    )
    print("Processed query:", processed_query)
    
    # --- Prepare query vector ---
    q_vector = np.zeros(num_terms)
    for token in processed_query:
        if token in term_to_index:
            i = term_to_index[token]
            tf = 1 + np.log(1)  # term occurs once
            q_vector[i] = tf * global_weights[i]
    
    # --- Apply boosting ---
    scientific_boost_factor = 5
    technical_boost_factor = 1.2
    for token in processed_query:
        if token in term_to_index:
            idx = term_to_index[token]
            if token in TERMES_SCIENTIFIQUES_STOCK:
                q_vector[idx] *= scientific_boost_factor
            elif token in TERMES_TECHNIQUES_STOCK:
                q_vector[idx] *= technical_boost_factor
    
    # --- Fold-in the query (using pre-calculated components) ---
    V_k = lsa.components_[:k, :]  # shape (k, num_docs)
    sigma_k = lsa.singular_values_[:k]  # shape (k,)
    
    # Reconstruct U_k if needed (or you could save it in the model)
    U_k = A_dense @ V_k.T  # shape (num_terms, k)
    U_k = U_k / sigma_k  # broadcasting
    
    # Project query to LSA space
    sigma_inv = np.diag(1 / sigma_k)
    q_concept = q_vector @ U_k @ sigma_inv  # 1 x k
    
    # --- Calculate similarities ---
    similarities = cosine_similarity(q_concept.reshape(1, -1), document_concepts)  # (1 x num_docs)
    
    # --- Get top matches ---
    top_idx = np.argsort(similarities[0])[::-1][:top_n]
    
    retrieved_documents = [all_documents[idx] for idx in top_idx]
    
    # Print results (optional)
    for rank, idx in enumerate(top_idx, start=1):
        print(f"{rank}. Document: {all_documents[idx]} — similarity: {similarities[0][idx]:.4f}")
    
    return retrieved_documents

# Usage example:
r = lsa_search("Je veux semer Petroselinum crispum avec arrosage modéré")
#for i, doc in enumerate(r):
    # print(f"{i+1}. Document: {doc}")