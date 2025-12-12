import json
from scipy.sparse import coo_matrix
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
import matplotlib.pyplot as plt
from preprocess_query import preprocess_query
from charger_stock_scientifique import charger_stock_scientifique
from sklearn.metrics.pairwise import cosine_similarity

def lsa_search(query :str) :
    # Load data
    inverted_index = json.load(open('../../../indexer/Base_Index.json', 'r', encoding='utf-8'))
    doc_term_counts = json.load(open('../../../indexer/document_lengths.json', 'r', encoding='utf-8'))

    # === Build term and document indices ===
    all_terms = list(inverted_index.keys())
    term_to_index = {term: i for i, term in enumerate(all_terms)}

    all_documents = sorted({doc for d in inverted_index.values() for doc in d})
    doc_to_index = {doc: j for j, doc in enumerate(all_documents)}

    num_terms = len(all_terms)
    num_docs  = len(all_documents)

    print("Terms:", num_terms)
    print("Documents:", num_docs)

    # === Compute TF (log-scaled) and needed sums ===
    # First pass: collect raw frequencies to compute entropy
    term_total_freqs = np.zeros(num_terms)

    for term, docs in inverted_index.items():
        i = term_to_index[term]
        term_total_freqs[i] = sum(docs.values())

    # === Compute Log-Entropy global weights ===
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
        global_weights[i] = 1 - entropy   # final global weight

    # === Build the weighted matrix ===
    row_indices = []
    col_indices = []
    data_values = []

    for term, docs in inverted_index.items():
        i = term_to_index[term]
        gw = global_weights[i]

        for doc, freq in docs.items():
            j = doc_to_index[doc]

            # Local weight: log TF
            if freq > 0:
                local_tf = 1 + np.log(freq)
            else:
                local_tf = 0

            weight = local_tf * gw

            row_indices.append(i)
            col_indices.append(j)
            data_values.append(weight)

    A = coo_matrix((data_values, (row_indices, col_indices)), shape=(num_terms, num_docs))

    print("Matrix shape:", A.shape)

    # === Export to CSV ===
    df_A = pd.DataFrame.sparse.from_spmatrix(A, index=all_terms, columns=all_documents)
    df_A.to_csv("lsa_weighted_matrix.csv", encoding="utf-8")

    print("✔ Exported to lsa_weighted_matrix.csv")


    max_k = min(num_terms, num_docs)   # With 95 docs → max_k = 95

    svd = TruncatedSVD(
        n_components=max_k,
        n_iter=12,
        random_state=0
    )

    svd.fit(A)

    singular_values = svd.singular_values_
    explained       = svd.explained_variance_ratio_
    cum_explained   = np.cumsum(explained)

    # ---- Print top components summary ----
    print("\n=== Singular Values (first 20) ===")
    for i, s in enumerate(singular_values[:20], start=1):
        print(f"k={i:2d} → singular={s:.4f}  explained={explained[i-1]*100:.2f}%  cumulative={cum_explained[i-1]*100:.2f}%")

    # ---- Scree plot ----
    # plt.figure(figsize=(7,4))
    # plt.plot(range(1, max_k+1), singular_values, marker='o')
    # plt.title("Scree Plot (Singular Values)")
    # plt.xlabel("k (Number of Components)")
    # plt.ylabel("Singular Value")
    # plt.grid(True)
    # plt.show()

    # # ---- Cumulative variance plot ----
    # plt.figure(figsize=(7,4))
    # plt.plot(range(1, max_k+1), cum_explained, marker='o')
    # plt.title("Cumulative Explained Variance")
    # plt.xlabel("k")
    # plt.ylabel("Cumulative Explained Variance")
    # plt.grid(True)
    # plt.show()

    print("\n✔ SVD analysis complete — use plots + table above to pick k.")

    k = 30
    print(f"\n=== Performing final LSA with k = {k} ===")

    # --- FIXES 1 & 2 APPLIED HERE ---
    # Use a new TruncatedSVD instance for the final reduction
    lsa = TruncatedSVD(n_components=k, n_iter=12, random_state=0)
    lsa.fit(A)

    # A_k = U_k * Sigma_k. This is the new vector space for the terms.
    term_concepts = lsa.transform(A)

    # components_ = V_k^T. Transposing gives V_k (new vector space for documents).
    document_concepts = lsa.components_.T

    print("\nShapes:")
    print("Term–concept matrix:", term_concepts.shape)
    print("Document–concept matrix:", document_concepts.shape)

    # === Save to CSV ===
    df_terms_k = pd.DataFrame(term_concepts,index=all_terms,columns=[f"concept_{i+1}" for i in range(k)])

    df_docs_k = pd.DataFrame(document_concepts,index=all_documents,columns=[f"concept_{i+1}" for i in range(k)])

    df_terms_k.to_csv("lsa_terms_k30.csv", encoding="utf-8")
    df_docs_k.to_csv("lsa_documents_k30.csv", encoding="utf-8")

    print("\n✔ Saved:")
    print(" - lsa_terms_k30.csv      (terms → concepts)")
    print(" - lsa_documents_k30.csv  (documents → concepts)")

    FICHIER_STOCK_SCIENTIFIQUE = "../../../docs/mot_scientifique/protected_terms.json"
    FICHIER_STOCK_TECHNIQUE = "../../../docs/mot_technique/protected_concepts.json"
    TERMES_SCIENTIFIQUES_STOCK = charger_stock_scientifique(FICHIER_STOCK_SCIENTIFIQUE) 
    TERMES_TECHNIQUES_STOCK = charger_stock_scientifique(FICHIER_STOCK_TECHNIQUE)
    MAX_NGRAM_SCIENTIFIQUE = 4

    #query = "Plantes médicinales pour le traitement de la fièvre"
    #query = "Je veux semer Petroselinum crispum avec arrosage modéré"
    processed_query = preprocess_query(query, TERMES_SCIENTIFIQUES_STOCK | TERMES_TECHNIQUES_STOCK , MAX_NGRAM_SCIENTIFIQUE)
    print(processed_query)


    # --- 2. Extract top-k singular values and components ---
    sigma_k = svd.singular_values_[:k]          # shape (k,)
    V_k = svd.components_[:k, :]                # shape (k, num_docs)



    # --- 3. Reconstruct approximate term-concept matrix U_k (terms × k) ---
    # term_concepts = A_dense @ V_k.T / sigma_k
    A_dense = A.toarray()                        # convert sparse to dense if feasible
    U_k = A_dense @ V_k.T                        # shape (num_terms, k)
    U_k = U_k / sigma_k                          # broadcasting: divide each column by corresponding singular value


    # --- 4. Prepare the query vector ---
    q_vector = np.zeros(num_terms)
    for token in processed_query:
        if token in term_to_index:
            i = term_to_index[token]
            tf = 1 + np.log(1)  # term occurs once
            q_vector[i] = tf * global_weights[i]


    scientific_boost_factor = 5
    technical_boost_factor = 1.2
    for token in processed_query:
        if token in term_to_index:
            idx = term_to_index[token]
            if token in TERMES_SCIENTIFIQUES_STOCK:
                q_vector[idx] *= scientific_boost_factor
                print("Scientific:", token)
            elif token in TERMES_TECHNIQUES_STOCK:
                q_vector[idx] *= technical_boost_factor
                print("Technical:", token)


    # --- 5. Fold-in the query ---
    sigma_inv = np.diag(1 / sigma_k)             # inverse of diagonal singular values
    q_concept = q_vector @ U_k @ sigma_inv       # 1 x k

    print("Query vector in LSA space (shape):", q_concept.shape)
    print("Query vector:", q_concept)

    #--- 7. Get top matches ---
    # q_concept shape: (1, k)
    similarities = cosine_similarity(q_concept.reshape(1, -1), document_concepts)  # (1 x num_docs)

    top_idx = np.argsort(similarities[0])[::-1][:30] 
    for rank, idx in enumerate(top_idx, start=1):
        print(f"{rank}. Document: {all_documents[idx]} — similarity: {similarities[0][idx]:.4f}")

    print(len(TERMES_TECHNIQUES_STOCK))
    print(len(TERMES_SCIENTIFIQUES_STOCK))

    retrieved_documents=[all_documents[idx] for idx in top_idx]
    return retrieved_documents

r=lsa_search("Je veux semer Petroselinum crispum avec arrosage modéré")
for i in range (0,30) :
        print(f"{i+1}. Document: {r[i]}")
