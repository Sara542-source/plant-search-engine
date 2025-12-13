import json
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from sklearn.decomposition import TruncatedSVD

def build_lsa_model(k=30):
    inverted_index = json.load(open('../../../indexer/Base_Index.json', 'r', encoding='utf-8'))
    
    all_terms = list(inverted_index.keys())
    term_to_index = {term: i for i, term in enumerate(all_terms)}
    all_documents = sorted({doc for d in inverted_index.values() for doc in d})
    doc_to_index = {doc: j for j, doc in enumerate(all_documents)}
    
    num_terms = len(all_terms)
    num_docs = len(all_documents)

    # 2. Compute Log-Entropy global weights
    term_total_freqs = np.zeros(num_terms)
    for term, docs in inverted_index.items():
        term_total_freqs[term_to_index[term]] = sum(docs.values())

    global_weights = np.zeros(num_terms)
    for term, docs in inverted_index.items():
        i = term_to_index[term]
        total = term_total_freqs[i]
        if total > 0:
            entropy_sum = sum((freq/total) * np.log(freq/total) for freq in docs.values())
            entropy = -entropy_sum / np.log(num_docs)
            global_weights[i] = 1 - entropy

    # 3. Build the weighted matrix
    row_indices, col_indices, data_values = [], [], []
    for term, docs in inverted_index.items():
        i = term_to_index[term]
        gw = global_weights[i]
        for doc, freq in docs.items():
            j = doc_to_index[doc]
            local_tf = 1 + np.log(freq) if freq > 0 else 0
            row_indices.append(i)
            col_indices.append(j)
            data_values.append(local_tf * gw)

    A = coo_matrix((data_values, (row_indices, col_indices)), shape=(num_terms, num_docs))

    # 4. SVD Final Reduction
    lsa = TruncatedSVD(n_components=k, n_iter=12, random_state=0)
    lsa.fit(A)
    
    # Calculate U_k (Term-Concept projection matrix)
    # U_k = A * V * Sigma^-1
    sigma_k = lsa.singular_values_
    V_k_T = lsa.components_ 
    U_k = (A.toarray() @ V_k_T.T) / sigma_k

    # 5. Save everything for the search function
    # Save matrices as numpy binaries for speed
    np.save("lsa_document_concepts.npy", lsa.components_.T) # Document-concept space
    np.save("lsa_U_k.npy", U_k)                            # Term-concept projection
    np.save("lsa_sigma_k.npy", sigma_k)                    # Singular values
    np.save("lsa_global_weights.npy", global_weights)      # Global weights
    
    # Save structural metadata
    metadata = {
        "all_terms": all_terms,
        "all_documents": all_documents,
        "k": k
    }
    with open("lsa_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f)

    print(f"✔ Model built and saved with k={k}")

build_lsa_model()
