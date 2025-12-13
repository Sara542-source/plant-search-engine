import os
import json
import math
from flask import Flask, render_template, request, send_from_directory
from pypdf import PdfReader 
from googleapiclient.discovery import build

try:
    # Ce chemin suppose que 'app.py' est à la racine de l'application Flask
    # et que 'search_service.py' est dans Model/Model_vectoriel/
    from Model.Model_vectoriel.search_service import rechercher_smart_fallback
    # L'index et les ressources sont chargés une seule fois ici à l'importation.
except ImportError as e:
    print(f"Erreur d'importation du moteur de recherche: {e}")
    print("Assurez-vous que le chemin d'importation 'Model.Model_vectoriel.search_service' est correct.")
    rechercher_smart_fallback = None # Prévient les erreurs si l'importation échoue

app = Flask(__name__)

#API de youtube
API_KEY = "AIzaSyA_wxvkxlTTxQlNGtHPPbcL5497aVymQsY" 
DOCS_FOLDER = os.path.join(os.getcwd(), 'docs')

# --- FONCTIONS UTILITAIRES (HELPERS) ---

def extract_pdf_title_and_snippet(pdf_path):
    """
    1. Trouve le TITRE (le texte avec la plus grande police sur la page 1).
    2. Trouve le SNIPPET (le reste du texte).
    3. Renvoie None pour l'image (car c'est un PDF).
    """
    title = ""
    snippet = ""
    max_font_size = 0
    
    try:
        reader = PdfReader(pdf_path)
        page = reader.pages[0]
        
        def visitor_body(text,  fontSize):
            nonlocal title, max_font_size, snippet
            if text and len(text.strip()) > 1 and fontSize is not None:
                if fontSize > max_font_size:
                    max_font_size = fontSize
                    title = text.strip()
                elif fontSize == max_font_size:
                    title += " " + text.strip()
                else:
                    snippet += text + " "

        page.extract_text(visitor_text=visitor_body)
        
        if not title: title = os.path.basename(pdf_path)
        if not snippet: snippet = page.extract_text()
            
    except Exception as e:
        title = "Document PDF"
        snippet = f"Erreur lecture: {str(e)}"

    snippet = snippet.replace('\n', ' ')[:300] + "..."
    return title, snippet, None

def get_json_info(json_path):
    """Extrait le nom scientifique, le résumé ET l'image"""
    title = ""
    snippet = ""
    image_url = None 
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 1. LE TITRE
            infos_generales = data.get('infos_generales', {})
            title = infos_generales.get('nom_scientifique', 'Plante Inconnue')
            
            # 2. LE SNIPPET
            source_data = data.get('source_data', {})
            snippet = source_data.get('resume')
            
            if not snippet:
                texte_complet = source_data.get('texte_complet', {})
                snippet = texte_complet.get('introduction', '')

            # 3. L'IMAGE 
            galerie = data.get('galerie_images', [])
            if isinstance(galerie, list) and len(galerie) > 0:
                image_url = galerie[0]

    except Exception as e:
        title = "Erreur JSON"
        snippet = str(e)
        
    if not snippet: snippet = "Pas de description disponible."
    if len(snippet) > 300: snippet = snippet[:300] + "..."
        
    return title, snippet, image_url

def build_rag_prompt(query, context_text):
    return 0

def call_llm(prompt):
    return 0

def get_ai_rag_response(query, context_text):
    """
    RAG PUR : Ne génère une réponse que si un document (contexte) est trouvé.
    """
    # Si aucun contexte n'est fourni, on ne renvoie RIEN (pas de fallback générique)
    if not context_text:
        return None

    # Si on a un document, on génère le bloc HTML vert (RAG)
    return f"""
    <div style="border-left: 4px solid #4ade80; padding-left: 15px;">
        <strong style="color: #4ade80;">🔍 Analyse RAG (Basée sur vos documents) :</strong><br>
        <em style="font-size: 0.9em; opacity: 0.8; display:block; margin-bottom:10px;">
            Contexte utilisé : "{context_text[:120]}..."
        </em>
        En croisant votre recherche <strong>"{query}"</strong> avec ce document, l'analyse indique que :
        <ul style="margin-top:5px; margin-bottom:5px;">
            <li>Ce sujet est traité spécifiquement dans le document détecté.</li>
            <li>Les données techniques (voir extrait) correspondent à votre requête.</li>
        </ul>
        Cette synthèse est générée à partir du contenu local ci-dessous.
    </div>
    """

def search_youtube(query):
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        request = youtube.search().list(
            part="snippet",
            maxResults=4,
            q=query,
            type="video"
        )
        response = request.execute()
        
        videos = []
        for item in response['items']:
            videos.append({
                'title': item['snippet']['title'],
                'video_id': item['id']['videoId']
            })
        return videos
    except Exception as e:
        print(f"Erreur YouTube: {e}")
        return []
    

# --- ROUTES FLASK ---
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5
    
    youtube_videos = search_youtube(query) if query else []
    
    # =========================================================================
    # 2. APPEL DU MOTEUR DE RECHERCHE ET MISE EN FORME DES RÉSULTATS
    # =========================================================================
    base_results = []
    if query and rechercher_smart_fallback:
        # Appelle le moteur de recherche pour obtenir les documents classés.
        raw_results = rechercher_smart_fallback(query)
        
        # Structure les résultats bruts en ajoutant 'score' et 'method'
        base_results = [
            {'filename': res['doc_id'], 'score': res['score'], 'method': res['method_used']} 
            for res in raw_results
        ]
    
    first_doc_context = ""
    
    if len(base_results) > 0:
        first_file = base_results[0]['filename']

        if first_file.endswith('.json'):
            path = os.path.join(DOCS_FOLDER, 'Plantes', first_file)
            dtype = 'json'
        elif first_file.endswith('.pdf'):
            path = os.path.join(DOCS_FOLDER, 'Concepts', first_file)
            dtype = 'pdf'
        else:
            path = None

        # On lit le contenu du 1er fichier pour le donner à l'IA
        if path and os.path.exists(path):
            try:
                if dtype == 'json':
                    _, snippet, _ = get_json_info(path)
                    first_doc_context = snippet
                elif dtype == 'pdf':
                    _, snippet, _ = extract_pdf_title_and_snippet(path)
                    first_doc_context = snippet
            except Exception as e:
                print(f"Erreur lecture context IA: {e}")

    ai_answer = get_ai_rag_response(query, first_doc_context)

    processed_results = []

    for res in base_results:
        filename = res['filename']
        # Les scores et méthodes sont lus, mais non ajoutés au résultat final pour l'affichage
        score = res.get('score', 0.0)      
        method = res.get('method', 'N/A')  
        
        extracted_title = "Inconnu"
        snippet = ""
        extracted_image = None

        if filename.endswith('.json'):
            subfolder = 'Plantes'
            doc_type = 'json'
            filepath = os.path.join(DOCS_FOLDER, subfolder, filename)
            
            if os.path.exists(filepath):
                extracted_title, snippet, extracted_image = get_json_info(filepath)
            else: continue

        elif filename.endswith('.pdf'):
            subfolder = 'Concepts'
            doc_type = 'pdf'
            filepath = os.path.join(DOCS_FOLDER, subfolder, filename)
            
            if os.path.exists(filepath):
                extracted_title, snippet, extracted_image = extract_pdf_title_and_snippet(filepath)
            else: continue
        else:
            continue
            
        processed_results.append({
            'id': filename,
            'title': extracted_title,
            'snippet': snippet,
            'type': doc_type,
            'image': extracted_image 
            # Le score et la méthode sont exclus ici pour l'affichage
        })
    
    # --- LOGIQUE DE PAGINATION ---
    total_results = len(processed_results)
    total_pages = math.ceil(total_results / per_page)
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated_results = processed_results[start:end]
    
    return render_template('results.html', 
                           query=query, 
                           results=paginated_results, 
                           page=page, 
                           total_pages=total_pages,
                           ai_answer=ai_answer,
                           videos=youtube_videos)

@app.route('/doc/<filename>')
def document(filename):
    if filename.endswith('.json'):
        filepath = os.path.join(DOCS_FOLDER, 'Plantes', filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return render_template('document_json.html', data=data)
        except Exception as e:
            # Affiche l'erreur réelle (Syntaxe ou Fichier)
            return f"<h1>Erreur technique</h1><p>{str(e)}</p>"

    elif filename.endswith('.pdf'):
        return render_template('document_pdf.html', filename=filename)
    
    return "Format non supporté"

@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(os.path.join(DOCS_FOLDER, 'Concepts'), filename)

if __name__ == '__main__':
    app.run(debug=True)