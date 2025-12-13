import re
import spacy
import json
def preprocess_query(query_text: str, stock_scientifique: set, max_n: int = 4) -> list[str]:
    """
    Process a raw query string the same way documents were processed:
    1. Tokenize
    2. Recognize multi-word scientific terms
    3. Lemmatisation + filtering for remaining tokens
    Returns a list of processed tokens ready for projection in LSA.
    """
    nlp = spacy.load('fr_core_news_sm')
    # --- 1. Clean text: remove numbers like in documents ---
    query_text_clean = re.sub(r'(\d+[\.,]?\d*)\s*(%|ml|g|cm|mm|m|l)?', ' ', query_text, flags=re.IGNORECASE)

    # --- 2. Tokenize with spaCy ---
    doc = nlp(query_text_clean)
    tokens_bruts0 = [token.text for token in doc if not token.is_space]

               # --- 8. Expand query using thesaurus ---Remove this section for normal processing--
    thesaurus = json.load(open('../../docs/Thesaurus//thesaurus_complet.json', 'r', encoding='utf-8'))
    expansion_terms = []
    for token in tokens_bruts0:
        if token in thesaurus:
            entry = thesaurus[token]
            # Collect RT, UF, SN terms
            for field in ['BT', 'UF']:
                expansion_terms.extend(entry.get(field, []))
            # For SN, tokenize description and keep meaningful words
            #sn_text = entry.get('SN', '')
            #expansion_terms.extend(sn_text.split())
    tokens_bruts = tokens_bruts0 + expansion_terms



    # --- 3. Recognize scientific/multi-word terms ---
    mots_scientifiques = []
    indices_captures = set()
    tokens_restants = []

    i = 0
    while i < len(tokens_bruts):
        if i in indices_captures:
            i += 1
            continue
        terme_trouve = False
        for n in range(min(max_n, len(tokens_bruts) - i), 0, -1):
            ngram_tokens = tokens_bruts[i:i+n]
            ngram_candidat = " ".join(ngram_tokens).lower().strip()
            if ngram_candidat in stock_scientifique:
                mots_scientifiques.append(ngram_candidat)
                for j in range(n):
                    indices_captures.add(i + j)
                i += n
                terme_trouve = True
                break
        if not terme_trouve:
            i += 1

    # Remaining tokens not part of scientific terms
    tokens_restants = [tokens_bruts[i] for i in range(len(tokens_bruts)) if i not in indices_captures]

    # --- 4. Lemmatize + filter remaining tokens ---
    texte_restant = " ".join(tokens_restants).lower()
    doc2 = nlp(texte_restant)
    stop_words = nlp.Defaults.stop_words
    mots_normalises = []
    for token in doc2:
        lemma_text = token.lemma_.lower().strip()
        if (
            not token.is_punct and
            token.is_alpha and
            not token.is_stop and
            len(lemma_text) > 1
        ):
            mots_normalises.append(lemma_text)

    # --- 5. Combine scientific terms + lemmatized tokens ---
    final_tokens = mots_scientifiques + mots_normalises
    return final_tokens