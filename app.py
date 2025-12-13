import os
import json
import math
from flask import Flask, render_template, request, send_from_directory
from pypdf import PdfReader 

app = Flask(__name__)

# Config: Le chemin vers le dossier racine 'docs'
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
        
        def visitor_body(text, cm, tm, fontDict, fontSize):
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
    
    # --- CORRECTION 1 : ON RENVOIE 3 VALEURS (La 3ème est None pour l'image) ---
    return title, snippet, None

def get_json_info(json_path):
    """Extrait le nom scientifique, le résumé ET l'image"""
    title = ""
    snippet = ""
    image_url = None # Par défaut
    
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

            # 3. L'IMAGE (CORRECTION 2 : AJOUT DE L'EXTRACTION)
            galerie = data.get('galerie_images', [])
            if isinstance(galerie, list) and len(galerie) > 0:
                image_url = galerie[0]

    except Exception as e:
        title = "Erreur JSON"
        snippet = str(e)
        
    if not snippet: snippet = "Pas de description disponible."
    if len(snippet) > 300: snippet = snippet[:300] + "..."
        
    # --- ON RENVOIE 3 VALEURS ---
    return title, snippet, image_url

def get_ai_rag_response(query):
    """
    Simule une réponse RAG (IA).
    """
    return f"""
    <strong>Basé sur les documents analysés concernant "{query}" :</strong><br><br>
    La <em>{query}</em> est souvent citée dans nos archives botaniques pour ses propriétés médicinales et ornementales. 
    Les documents identifient plusieurs usages clés :
    <ul>
        <li>Utilisation en phytothérapie traditionnelle.</li>
        <li>Besoins spécifiques en irrigation (voir document PDF associé).</li>
        <li>Aires de répartition géographique limitées aux climats tempérés.</li>
    </ul>
    Cette synthèse est générée automatiquement à partir des documents les plus pertinents.
    """

# --- ROUTES FLASK ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5
    
    # 1. APPEL DE LA FONCTION RAG
    ai_answer = get_ai_rag_response(query)
    
    # Simulation des résultats
    base_results = [
        {'filename': '265454.json'}, 
        {'filename': 'Arrosage.pdf'},
        {'filename': '5945.json'},
         {'filename': '385323.json'}
    ]
    mock_results = base_results 
    
    processed_results = []
    
    for res in mock_results:
        filename = res['filename']
        
        # Initialisation explicite
        extracted_title = "Inconnu"
        snippet = ""
        extracted_image = None

        # Logique de tri
        if filename.endswith('.json'):
            subfolder = 'Plantes'
            doc_type = 'json'
            filepath = os.path.join(DOCS_FOLDER, subfolder, filename)
            
            if os.path.exists(filepath):
                # --- ATTEND 3 VALEURS (Titre, Snippet, Image) ---
                extracted_title, snippet, extracted_image = get_json_info(filepath)
            else: continue

        elif filename.endswith('.pdf'):
            subfolder = 'Concepts'
            doc_type = 'pdf'
            filepath = os.path.join(DOCS_FOLDER, subfolder, filename)
            
            if os.path.exists(filepath):
                # --- ATTEND 3 VALEURS (Titre, Snippet, None) ---
                extracted_title, snippet, extracted_image = extract_pdf_title_and_snippet(filepath)
            else: continue
        else:
            continue
            
        processed_results.append({
            'id': filename,
            'title': extracted_title,
            'snippet': snippet,
            'type': doc_type,
            'image': extracted_image # L'image est maintenant correctement passée
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
                           ai_answer=ai_answer)

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