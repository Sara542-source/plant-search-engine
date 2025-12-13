import os
import json
import math
from flask import Flask, render_template, request, send_from_directory
from pypdf import PdfReader 
from googleapiclient.discovery import build
from openai import OpenAI
client = OpenAI(api_key="mon api")

try:
    from Model.Model_vectoriel.search_service import rechercher_smart_fallback
    # L'index et les ressources sont chargés une seule fois ici à l'importation.
except ImportError as e:
    print(f"Erreur d'importation du moteur de recherche: {e}")
    print("Assurez-vous que le chemin d'importation 'Model.Model_vectoriel.search_service' est correct.")
    rechercher_smart_fallback = None # Prévient les erreurs si l'importation échoue

app = Flask(__name__)

#API de youtube
API_KEY = "" 
DOCS_FOLDER = os.path.join(os.getcwd(), 'docs')

# --- FONCTIONS UTILITAIRES (HELPERS) ---

def extract_pdf_title_and_snippet(pdf_path):
    """
    Stratégie robuste d'extraction pour PDF :
    1. Essaie de lire les métadonnées officielles du PDF (Souvent le titre propre s'y trouve).
    2. Sinon, cherche le texte avec la plus grande police sur la 1ère page.
    3. Sinon, prend le nom du fichier.
    Pour le snippet : Extrait le texte brut du début.
    """
    title = ""
    snippet = ""
    
    try:
        reader = PdfReader(pdf_path)
        
        # --- PLAN A : Les Métadonnées (Le plus propre) ---
        if reader.metadata and reader.metadata.title:
            title = reader.metadata.title.strip()
        
        # Récupération de la première page pour l'analyse
        if len(reader.pages) > 0:
            page = reader.pages[0]
            raw_text = page.extract_text()
            
            # --- PLAN B : Analyse de la police (Si pas de métadonnées) ---
            if not title:
                max_font_size = 0
                temp_title = ""
                
                # La signature correcte de visitor_body prend 5 arguments
                def visitor_body(text, cm, tm, fontDict, fontSize):
                    nonlocal temp_title, max_font_size
                    # On cherche un texte significatif (pas juste un espace)
                    if text and len(text.strip()) > 3 and fontSize is not None:
                        if fontSize > max_font_size:
                            max_font_size = fontSize
                            temp_title = text.strip()
                        elif fontSize == max_font_size:
                            temp_title += " " + text.strip()

                try:
                    # On ignore les erreurs mineures d'extraction
                    page.extract_text(visitor_text=visitor_body)
                    if temp_title:
                        title = temp_title
                except Exception:
                    pass # Si l'analyse visuelle échoue, on continue

            # --- Construction du SNIPPET ---
            # On prend le texte brut, on nettoie les sauts de ligne bizarres
            if raw_text:
                # On enlève le titre du snippet pour ne pas le répéter
                clean_text = raw_text.replace(title, '') if title else raw_text
                snippet = clean_text.replace('\n', ' ').strip()
        
    except Exception as e:
        print(f"Erreur PDF {pdf_path}: {e}")
        snippet = "Lecture impossible."

    # --- PLAN C : Le nom de fichier (Secours ultime) ---
    if not title or len(title) < 3:
        title = os.path.basename(pdf_path).replace('.pdf', '').replace('_', ' ')

    # Troncature propre du snippet
    if snippet:
        snippet = snippet[:300] + "..."
    else:
        snippet = "Aperçu non disponible."

    # On renvoie toujours 3 valeurs (Titre, Snippet, Image=None)
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
    """
    Construit le prompt pour le LLM en RAG.
    Le prompt inclut :
    - La requête utilisateur
    - Le contexte (extrait du doc trouvé)
    """
    prompt = f"""
Vous êtes un assistant spécialisé en botanique. 
Répondez de manière concise à la requête suivante en utilisant seulement le contexte fourni.

Contexte du document : 
"{context_text}"

Requête de l'utilisateur : 
"{query}"

Réponse :
"""
    return prompt

def call_llm(prompt):
    try:
        response = client.responses.create(
            model="gpt-5.2",
            input=prompt,
            temperature=0.2  # plus précis, moins créatif
        )
        # Le texte généré est dans response.output_text
        return response.output_text
    except Exception as e:
        print(f"Erreur LLM : {e}")
        return "Impossible de générer une réponse pour le moment."

def get_ai_rag_response(query, context_text):
    """
    Génère une réponse RAG si un document est trouvé.
    """
    if not context_text:
        return None

    prompt = build_rag_prompt(query, context_text)
    llm_response = call_llm(prompt)

    # On renvoie un bloc HTML prêt à afficher dans results.html
    return f"""
    <div style="border-left: 4px solid #4ade80; padding-left: 15px;">
        <strong style="color: #4ade80;">🔍 Analyse RAG :</strong><br>
        <em style="font-size: 0.9em; opacity: 0.8; display:block; margin-bottom:10px;">
            Contexte utilisé : "{context_text[:120]}..."
        </em>
        {llm_response}
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