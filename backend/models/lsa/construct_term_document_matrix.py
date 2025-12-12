import json
from scipy.sparse import coo_matrix
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
import matplotlib.pyplot as plt


# Load data
inverted_index = json.load(open('Base_Index.json', 'r', encoding='utf-8'))
doc_term_counts = json.load(open('document_lengths.json', 'r', encoding='utf-8'))

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
plt.figure(figsize=(7,4))
plt.plot(range(1, max_k+1), singular_values, marker='o')
plt.title("Scree Plot (Singular Values)")
plt.xlabel("k (Number of Components)")
plt.ylabel("Singular Value")
plt.grid(True)
plt.show()

# ---- Cumulative variance plot ----
plt.figure(figsize=(7,4))
plt.plot(range(1, max_k+1), cum_explained, marker='o')
plt.title("Cumulative Explained Variance")
plt.xlabel("k")
plt.ylabel("Cumulative Explained Variance")
plt.grid(True)
plt.show()

print("\n✔ SVD analysis complete — use plots + table above to pick k.")
# After k = 3, the curve becomes smooth and flat.

# 2. Cumulative explained variance rule

# Common rule: choose k where cumulative variance is:
# 60% if many documents
# 70% if concept-heavy
# 80–90% if compression quality matters more than noise reduction

# For you (95 docs), a typical LSA would choose ~30–50 concepts.
# Let's find approximate variance coverage:  At k=20 → 44.58%

# Given this curve, to reach:
# 60% → probably around k ≈ 30–35
# 70% → around k ≈ 40–45
# 80% → around k ≈ 55–60

# 3. Practical LSA rule (best for search/query expansion)

# Academic IR studies (Deerwester et al., Landauer & Dumais, Manning et al.) recommend:

# k ≈ 100–300 for large corpora
# k ≈ 20–100 for small corpora
# k ≈ ⅓ of number of documents for small datasets

# Recommended band: ✔ k = 20–40
# 🎯 My recommendation for YOUR dataset :

# Based on: 95 documents
# Steep singular-value drop (biggest structure in first 3–10 values)
# Cumulative variance still rising steadily after 20
# 👉 Choose k = 30



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