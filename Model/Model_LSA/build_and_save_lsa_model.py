import json
from scipy.sparse import coo_matrix
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
import pickle

def build_and_save_lsa_model():
    """Build LSA model and save all necessary components. Run this only when your database changes."""
    
    # Load data
    inverted_index = json.load(open('../../indexer/Base_Index.json', 'r', encoding='utf-8'))
    doc_term_counts = json.load(open('../../indexer/document_lengths.json', 'r', encoding='utf-8'))

    # === Build term and document indices ===
    all_terms = list(inverted_index.keys())
    term_to_index = {term: i for i, term in enumerate(all_terms)}

    all_documents = sorted({doc for d in inverted_index.values() for doc in d})
    doc_to_index = {doc: j for j, doc in enumerate(all_documents)}

    num_terms = len(all_terms)
    num_docs  = len(all_documents)

    print("Terms:", num_terms)
    print("Documents:", num_docs)

    # === Compute global weights ===
    term_total_freqs = np.zeros(num_terms)
    for term, docs in inverted_index.items():
        i = term_to_index[term]
        term_total_freqs[i] = sum(docs.values())

    global_weights = np.zeros(num_terms)
    for term, docs in inverted_index.items():
        i = term_to_index[term]
        total = term_total_freqs[i]

        if total == 0:
            continue

        entropy_sum = 0.0
        for freq in docs.values():
            p_td = freq / total
            entropy_sum += p_td * np.log(p_td)

        entropy = -entropy_sum / np.log(num_docs)
        global_weights[i] = 1 - entropy

    # === Build the weighted matrix ===
    row_indices = []
    col_indices = []
    data_values = []

    for term, docs in inverted_index.items():
        i = term_to_index[term]
        gw = global_weights[i]

        for doc, freq in docs.items():
            j = doc_to_index[doc]

            if freq > 0:
                local_tf = 1 + np.log(freq)
            else:
                local_tf = 0

            weight = local_tf * gw

            row_indices.append(i)
            col_indices.append(j)
            data_values.append(weight)

    A = coo_matrix((data_values, (row_indices, col_indices)), shape=(num_terms, num_docs))

    # === Export matrix to CSV (optional) ===
    df_A = pd.DataFrame.sparse.from_spmatrix(A, index=all_terms, columns=all_documents)
    df_A.to_csv("lsa_weighted_matrix.csv", encoding="utf-8")

    # === Choose k and perform LSA ===
    k = 30
    lsa = TruncatedSVD(n_components=k, n_iter=12, random_state=0)
    lsa.fit(A)

    # Get the document-concept matrix
    document_concepts = lsa.components_.T  # shape: (num_docs, k)

    # === Save everything needed for querying ===
    lsa_model = {
        'term_to_index': term_to_index,
        'doc_to_index': doc_to_index,
        'all_terms': all_terms,
        'all_documents': all_documents,
        'global_weights': global_weights,
        'lsa_model': lsa,  # The fitted SVD model
        'document_concepts': document_concepts,
        'A_dense': A.toarray(),  # For U_k calculation
        'num_terms': num_terms,
        'num_docs': num_docs
    }
    
    # Save to pickle file
    with open('lsa_model.pkl', 'wb') as f:
        pickle.dump(lsa_model, f)
    
    print("✔ LSA model built and saved to 'lsa_model.pkl'")
    print("✔ Document-concept matrix shape:", document_concepts.shape)
    
    return lsa_model

# Run this only when your database changes
build_and_save_lsa_model()