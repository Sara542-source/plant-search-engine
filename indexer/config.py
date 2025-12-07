# config.py
import os

# 1. On repère où est ce fichier config.py sur votre ordinateur
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. On définit où sont les données par rapport à ce fichier
DATA_DIR_JSON = os.path.join(BASE_DIR, '..', 'docs', 'Plantes')
DATA_DIR_PDF = os.path.join(BASE_DIR, '..', 'docs', 'Concepts')

# 3. Où va-t-on sauvegarder l'index final ?
INDEX_OUTPUT_PATH = os.path.join(BASE_DIR, 'index_inversé.json')

def get_stop_words():
    """
    Retourne un set de mots vides (Français + Darija + Anglais basique)
    Utiliser un SET est beaucoup plus rapide qu'une LISTE pour la recherche.
    """
    stop_words = {
        # --- FRANÇAIS STANDARD (Articles, pronoms, prépositions) ---
        "au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du", "elle", "en", "et", "eux",
        "il", "je", "la", "le", "leur", "lui", "ma", "mais", "me", "même", "mes", "moi", "mon",
        "ne", "nos", "notre", "nous", "on", "ou", "par", "pas", "pour", "qu", "que", "qui", "sa",
        "se", "ses", "son", "sur", "ta", "te", "tes", "toi", "ton", "tu", "un", "une", "vos", "votre",
        "vous", "c", "d", "j", "l", "m", "n", "s", "t", "y", "à", "ça", "là",

        # --- VERBES AUXILIAIRES (Être & Avoir - souvent inutiles en recherche) ---
        "été", "étant", "suis", "es", "est", "sommes", "êtes", "sont", "serai", "sera", "serons",
        "seront", "étais", "était", "étions", "étaient", "sois", "soit", "soyons", "soient",
        "eu", "ai", "as", "avons", "avez", "ont", "aurai", "aura", "aurons", "auront",
        "avais", "avait", "avions", "avaient", "aie", "ait", "ayons", "aient",

        # --- DARIJA MAROCAIN (Transcrit) ---
        "dyal", "dial",  # de/du
        "f", "fi",  # dans
        "men", "mn",  # de (from)
        "w", "o", "wa",  # et
        "li", "lli",  # qui/que
        "bach",  # pour
        "3la", "3ala",  # sur
        "kif",  # comment
        "wash",  # est-ce que
        "had",  # ce/cette
        "houwa", "hiya",  # il/elle

        # --- ANGLAIS (Au cas où tes PDF contiennent des termes scientifiques) ---
        "the", "of", "and", "in", "to", "is", "a", "for", "with"
    }

    return stop_words

