import json
import math
import re
import spacy
from collections import defaultdict, Counter
import os
from typing import Set, List, Dict, Tuple, Any

# =============================================================================
# VOS PARAMÈTRES ET CHEMINS (ASSUREZ-VOUS QU'ILS SONT CORRECTS DEPUIS L'APP FLASK)
# =============================================================================

# NOTE: Les chemins doivent être ajustés en fonction du répertoire de l'application Flask.
# Par exemple, si l'app est dans 'app/' et les index dans '../indexer/', ajustez ici.
INDEX_FILE = "../../indexer/Base_Index.json"
DOC_LENGTHS_FILE = "../../indexer/document_lengths.json"
FICHIER_CONCEPTS_CLES = "../../docs/mot_conceptuel/protected_concepts.json"
FICHIER_STOCK_SCIENTIFIQUE = "../../docs/mot_scientifique/protected_terms.json"
LOOKUP_FILE = "../../docs/Lookup/lookup.json"
THESAURUS_FILE = "../../docs/Thesaurus/thesaurus_complet.json"

LANGUE = 'fr_core_news_lg'
MAX_NGRAM_SCIENTIFIQUE = 4
CUTOFF_K = 30 # Le nombre de documents que la plateforme doit retourner

# Facteurs de Poids Spécifiques
SCIENTIFIC_BOOST_FACTOR = 2.0
CONCEPT_BOOST_FACTOR = 2.0
THESAURUS_BOOST_FACTOR = 2.0
DEBOOST_FACTOR = 0.5

# =============================================================================
# INITIALISATION ET CHARGEMENT DES RESSOURCES (À EXÉCUTER UNE SEULE FOIS)
# =============================================================================

# Fonctions de chargement sécurisé (gardées pour la complétude)
def safe_load_json(filepath: str, name: str) -> dict:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erreur critique au chargement de {name}: {e}")
        return {}

def load_terms_set(filepath: str, key: str) -> Set[str]:
    data = safe_load_json(filepath, f"Liste de {key}")
    if isinstance(data, list):
        terms_list = data
    elif isinstance(data, dict) and key in data:
        terms_list = data[key]
    elif isinstance(data, dict) and 'concepts' in data:
        terms_list = data['concepts']
    else:
        terms_list = list(data.keys())
    return set(t.lower().strip() for t in terms_list)

# Initialisation
try:
    nlp = spacy.load(LANGUE)
except OSError:
    print(f"🚨 Erreur: Modèle spaCy '{LANGUE}' non trouvé.")
    exit()

TERMES_SCIENTIFIQUES_STOCK = load_terms_set(FICHIER_STOCK_SCIENTIFIQUE, "scientific_terms")
CONCEPT_TERMS_SET = load_terms_set(FICHIER_CONCEPTS_CLES, "concepts")
LOOKUP_TABLE = safe_load_json(LOOKUP_FILE, "Lookup Table")
THESAURUS = safe_load_json(THESAURUS_FILE, "Thesaurus")
index_inverse = safe_load_json(INDEX_FILE, "Base Index")
doc_lengths = safe_load_json(DOC_LENGTHS_FILE, "Longueurs documents")
N_DOCS = len(doc_lengths)

if not N_DOCS:
    print("ATTENTION: Index vide. Le moteur de recherche ne fonctionnera pas.")

# =============================================================================
# FONCTIONS DE PRÉ-TRAITEMENT (Identiques aux précédentes)
# =============================================================================

def contient_caracteres_arabes(token: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', token))

def nettoyer_token_arabe(token: str) -> str:
    token = token.lower().strip()
    if token.startswith('ال'):
        return token[2:]
    return token

def normaliser_lemmatisation(tokens_restants: list) -> List[str]:
    texte_restant = " ".join(tokens_restants)
    doc = nlp(texte_restant.lower())
    mots_normalises = []
    tokens_deja_traites = set()

    for token in doc:
        token_text = token.text.strip()
        
        # LOGIQUE ARABE
        if contient_caracteres_arabes(token_text):
            token_normalise = nettoyer_token_arabe(token_text)
            if len(token_normalise) > 1 and token_normalise not in tokens_deja_traites:
                mots_normalises.append(token_normalise)
                tokens_deja_traites.add(token_normalise)
                
        # LOGIQUE FRANÇAISE/LATINE
        elif (
            not token.is_punct and token.is_alpha and not token.is_stop and len(token.lemma_.strip()) > 1
        ):
            lemme = token.lemma_.lower().strip()
            if lemme not in tokens_deja_traites:
                mots_normalises.append(lemme)
                tokens_deja_traites.add(lemme)
                
    for t in tokens_restants:
        if not re.search(r'[a-zA-ZÀ-ÿ]', t) and t.lower() not in tokens_deja_traites:
            mots_normalises.append(t.lower())
            tokens_deja_traites.add(t.lower())
            
    return mots_normalises

def identifier_termes_scientifiques(tokens: list, stock_scientifique: set, max_n: int) -> Tuple[List[str], List[str]]:
    # ... (fonction identique - omise ici pour la concision)
    mots_scientifiques = []
    indices_captures = set()
    i = 0
    while i < len(tokens):
        if i in indices_captures:
            i += 1
            continue
        terme_trouve = False
        for n in range(min(max_n, len(tokens) - i), 0, -1):
            ngram_candidat = " ".join(tokens[i:i+n]).lower().strip()
            if ngram_candidat in stock_scientifique:
                mots_scientifiques.append(ngram_candidat)
                for j in range(n): indices_captures.add(i + j)
                terme_trouve = True
                i += n
                break
        if not terme_trouve:
            i += 1
    tokens_restants = [tokens[i] for i in range(len(tokens)) if i not in indices_captures]
    return mots_scientifiques, tokens_restants


def traiter_requete_utilisateur(requete_texte: str) -> Tuple[List[str], List[str]]:
    mots_indexables = []
    mots_scientifiques_captures = []
    
    tokens_with_numbers = re.findall(r'[a-zA-ZÀ-ÿ\u0600-\u06FF]+|\d+[\.,]\d+|\d+|[%mlgcmh]', requete_texte, re.IGNORECASE)
    
    tokens_bruts_alpha = []
    for t in tokens_with_numbers:
        if re.search(r'[a-zA-ZÀ-ÿ\u0600-\u06FF]', t):
            tokens_bruts_alpha.append(t)
        else:
            mots_indexables.append(t.replace(',', '.'))

    mots_scientifiques, tokens_restants = identifier_termes_scientifiques(
        tokens_bruts_alpha, TERMES_SCIENTIFIQUES_STOCK, MAX_NGRAM_SCIENTIFIQUE
    )
    mots_scientifiques_captures.extend(mots_scientifiques)
    mots_indexables.extend(mots_scientifiques)
    
    mots_lemmatises = normaliser_lemmatisation(tokens_restants)
    mots_indexables.extend(mots_lemmatises)

    return [t for t in mots_indexables if t and len(t.strip()) > 0], mots_scientifiques_captures


# =============================================================================
# FONCTIONS DE PONDÉRATION ET CALCUL (Identiques aux précédentes)
# =============================================================================

def calculer_similarite_cosinus_ponderee(query_weights: Dict[str, float], index: dict) -> dict:
    scores_numerateur = defaultdict(float)
    longueurs_doc_carre = defaultdict(float)
    longueur_query_carre = 0
    idf_cache = {}
    
    for token, w_q in query_weights.items():
        if token in index:
            df = len(index[token])
            # La formule IDF
            idf = math.log((N_DOCS + 1) / (df + 1)) + 1
            idf_cache[token] = idf
            longueur_query_carre += w_q ** 2

    longueur_query = math.sqrt(longueur_query_carre)
    if longueur_query == 0: return {}
    
    for token, w_q in query_weights.items():
        if token in idf_cache:
            idf = idf_cache[token]
            
            for doc_id, tf_doc in index[token].items():
                w_d = tf_doc * idf
                scores_numerateur[doc_id] += w_q * w_d
                longueurs_doc_carre[doc_id] += w_d ** 2

    final_scores = {}
    for doc_id, numerateur in scores_numerateur.items():
        longueur_doc = math.sqrt(doc_lengths.get(doc_id, longueurs_doc_carre[doc_id]))
        
        if longueur_doc > 0 and longueur_query > 0:
            score = numerateur / (longueur_query * longueur_doc)
            final_scores[doc_id] = score
            
    return final_scores

def get_method1_query_weights_smart(initial_tokens: List[str], scientific_tokens: List[str]) -> Dict[str, float]:
    weights = Counter(initial_tokens)
    final_weights = {}
    
    scientific_boost_set = set()
    for n_gram in scientific_tokens:
        scientific_boost_set.update(n_gram.split())
        
    TERMES_PERTINENTS_SET = scientific_boost_set.union(TERMES_SCIENTIFIQUES_STOCK, CONCEPT_TERMS_SET)
    
    for token, count in weights.items():
        token_lower = token.lower()
        if token_lower in index_inverse:
            is_key_term = token_lower in TERMES_PERTINENTS_SET
            base_tf = float(count)
            
            if is_key_term:
                final_weights[token_lower] = base_tf * SCIENTIFIC_BOOST_FACTOR
            else:
                final_weights[token_lower] = base_tf * DEBOOST_FACTOR
        
    return final_weights

def get_method2_query_weights(initial_tokens: List[str], scientific_tokens: List[str], lookup: dict, thesaurus: dict) -> Dict[str, float]:
    final_query_weights = Counter(token.lower() for token in initial_tokens)
    termes_a_verifier_thesaurus = set()
    
    scientific_boost_set = set()
    for n_gram in scientific_tokens:
        scientific_boost_set.update(n_gram.split())
    for token in initial_tokens:
        token_lower = token.lower()
        if token_lower in TERMES_SCIENTIFIQUES_STOCK:
              scientific_boost_set.add(token_lower)
    
    tokens_to_lookup = scientific_boost_set if scientific_tokens else set(token.lower() for token in initial_tokens)

    for token in tokens_to_lookup:
        if token in lookup:
            termes_a_verifier_thesaurus.update(lookup[token])
        elif token in thesaurus:
              termes_a_verifier_thesaurus.add(token)
              
    for terme_index in termes_a_verifier_thesaurus:
        if terme_index in thesaurus:
            fiche = thesaurus[terme_index]
            expansion_tokens = fiche.get("BT", []) + fiche.get("UF", [])
            
            for terme in expansion_tokens:
                terme_lower = terme.lower()
                if terme_lower in index_inverse: 
                    if terme_lower not in final_query_weights:
                        final_query_weights[terme_lower] = THESAURUS_BOOST_FACTOR 
    
    for token in initial_tokens:
          token_lower = token.lower()
          base_tf = Counter(initial_tokens).get(token, 1)

          if token_lower in scientific_boost_set and token_lower in index_inverse:
              final_query_weights[token_lower] = base_tf * SCIENTIFIC_BOOST_FACTOR 
          elif token_lower not in final_query_weights and token_lower in index_inverse:
               final_query_weights[token_lower] = base_tf
               
    return {k: float(v) for k, v in final_query_weights.items() if k in index_inverse}


# =============================================================================
# FONCTIONS DE RECHERCHE CONCRÈTES (M1 et M2)
# =============================================================================

def rechercher_documents_method1_pondere(query: str, top_k: int) -> List[Tuple[str, float]]:
    initial_tokens, scientific_tokens = traiter_requete_utilisateur(query)
    if not initial_tokens:
        return []
    query_weights = get_method1_query_weights_smart(initial_tokens, scientific_tokens)
    scores = calculer_similarite_cosinus_ponderee(query_weights, index_inverse)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]

def rechercher_documents_method2_pondere(query: str, top_k: int) -> List[Tuple[str, float]]:
    initial_tokens, scientific_tokens = traiter_requete_utilisateur(query)
    if not initial_tokens:
        return []
    query_weights = get_method2_query_weights(initial_tokens, scientific_tokens, LOOKUP_TABLE, THESAURUS)
    scores = calculer_similarite_cosinus_ponderee(query_weights, index_inverse)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]

# =============================================================================
# FONCTION PRINCIPALE AVEC LOGIQUE DE BASCULE (SMART FALLBACK) POUR FLASK
# =============================================================================

def rechercher_smart_fallback(query: str) -> List[Dict[str, Any]]:
    """
    Fonction principale de recherche.
    1. Tente la recherche via la Méthode 1 (Pondération Intelligente).
    2. Si aucun résultat n'est trouvé, bascule vers la Méthode 2 (Expansion Sémantique).

    Args:
        query: La requête de l'utilisateur (str).

    Returns:
        Une liste de dictionnaires [{doc_id: str, score: float}], limitée à CUTOFF_K.
    """
    print(f"\n--- RECHERCHE DEMARRÉE : '{query}' ---")
    
    # 1. TENTATIVE N°1 : MÉTHODE 1 (Pondération Intelligente)
    print("Tentative 1/2 : Méthode 1 (Pondération Intelligente)...")
    resultats = rechercher_documents_method1_pondere(query, top_k=CUTOFF_K)

    if resultats:
        print(f"✅ Succès M1 : {len(resultats)} documents trouvés.")
        method_used = "Méthode 1"
    else:
        # 2. TENTATIVE N°2 : BASCULE VERS LA MÉTHODE 2 (Expansion Sémantique)
        print("❌ M1 n'a trouvé aucun résultat. Bascule vers la Méthode 2 (Expansion Sémantique)...")
        resultats = rechercher_documents_method2_pondere(query, top_k=CUTOFF_K)
        
        if resultats:
            print(f"✅ Succès M2 : {len(resultats)} documents trouvés par expansion sémantique.")
            method_used = "Méthode 2 (Fallback)"
        else:
            print("❌ M2 n'a trouvé aucun résultat. Recherche infructueuse.")
            method_used = "Aucune"

    # Formatage du résultat pour la plateforme Flask
    resultats_formates = [
        {"doc_id": doc_id, "score": score, "method_used": method_used} 
        for doc_id, score in resultats
    ]
    
    return resultats_formates


# =============================================================================
# EXEMPLE D'UTILISATION (Pour tester ce module directement)
# =============================================================================

if __name__ == "__main__":
    
    # Exemple 1 : Requête qui devrait réussir avec M1 (si "SDR" est un terme fort)
    print("\n" + "="*80)
    print("TEST 1: Requête forte (ex: 'SDR' ou terme scientifique connu)")
    print("="*80)
    resultat_fort = rechercher_smart_fallback("SDR") 
    
    if resultat_fort:
        print(f"\nRésultat final ({len(resultat_fort)} docs):")
        for item in resultat_fort[:5]:
            print(f"  - {item['doc_id']} | Score: {item['score']:.4f} | Source: {item['method_used']}")
    
    # Exemple 2 : Requête qui devrait échouer en M1 et passer par M2 (expansion)
    # (ATTENTION : Cette requête est hypothétique et dépend de votre Lookup/Thesaurus)
    print("\n" + "="*80)
    print("TEST 2: Requête faible (ex: terme avec synonyme dans le thésaurus)")
    print("="*80)
    resultat_faible = rechercher_smart_fallback("besoin d'eau")
    
    if resultat_faible:
        print(f"\nRésultat final ({len(resultat_faible)} docs):")
        for item in resultat_faible[:5]:
            print(f"  - {item['doc_id']} | Score: {item['score']:.4f} | Source: {item['method_used']}")
            
    # Exemple 3 : Requête arabe
    print("\n" + "="*80)
    print("TEST 3: Requête arabe (doit marcher en M1)")
    print("="*80)
    resultat_arabe = rechercher_smart_fallback("الكليبتوس")
    
    if resultat_arabe:
        print(f"\nRésultat final ({len(resultat_arabe)} docs):")
        for item in resultat_arabe[:5]:
            print(f"  - {item['doc_id']} | Score: {item['score']:.4f} | Source: {item['method_used']}")