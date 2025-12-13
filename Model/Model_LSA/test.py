import json
from typing import List, Dict, Any, Tuple
from lsa_search import lsa_search

EVALUATION_DATA_FILE = "../../docs/Test/test.json" 
# Le nombre maximum de documents retournés par le modèle, comme spécifié.
CUTOFF_K = 10 


# --- ÉTAPE 1: LA FONCTION DE MATCHING---

def placeholder_match_function(query: str) -> List[str]:
    retrieved = lsa_search(query)
    return retrieved[:CUTOFF_K] 
    

# --- ÉTAPE 2: CALCUL DES MÉTRIQUES POUR UNE SEULE REQUÊTE ---

def evaluate_query(
    query: str,
    relevant_docs: List[str],
    retrieved_docs: List[str]
) -> Dict[str, Any]:
    
    # Convertir en set pour des opérations d'intersection/différence efficaces
    R = set(relevant_docs) # Relevant (Pertinents)
    A = set(retrieved_docs) # Retrieved (Retournés par le modèle)
    
    # Calcul des composantes de la Matrice de Confusion (pour l'ensemble des documents retournés)
    
    # True Positives (TP): Pertinents ET Retournés
    TP = len(R.intersection(A))
    
    # False Positives (FP): Non Pertinents MAIS Retournés
    FP = len(A.difference(R))
    
    # False Negatives (FN): Pertinents MAIS Non Retournés
    FN = len(R.difference(A))
    
    # True Negatives (TN): Non Pertinents ET Non Retournés (Souvent omis en IR car dépendant 
    # de la taille du corpus total, mais peut être calculé si besoin)
    
    # Calcul des métriques
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "query": query,
        "TP": TP,
        "FP": FP,
        "FN": FN,
        "Precision": precision,
        "Recall": recall,
        "F1-Score": f1_score,
        "Relevant_Count": len(R),
        "Retrieved_Count": len(A)
    }


# --- ÉTAPE 3: EXÉCUTION DE L'ÉVALUATION GLOBALE ---

def run_evaluation(data_file: str):
    """
    Exécute le processus d'évaluation complet sur toutes les requêtes du fichier.
    """
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            evaluation_data: List[Dict[str, Any]] = json.load(f)
    except FileNotFoundError:
        print(f"ERREUR: Fichier non trouvé à l'emplacement: {data_file}")
        print("Veuillez vous assurer que le fichier JSON des requêtes est présent.")
        return
    except json.JSONDecodeError:
        print(f"ERREUR: Impossible de lire le fichier JSON: {data_file}. Vérifiez son format.")
        return

    print(f"--- Démarrage de l'évaluation sur {len(evaluation_data)} requêtes ---")
    
    # 1. Identifier tous les titres de documents du corpus pour la fonction placeholder
    all_relevant_titles = set()
    for item in evaluation_data:
        all_relevant_titles.update(item["relevant_documents"])
    # Ajouter d'autres documents au corpus total si nécessaire (non pertinent, par exemple)
    corpus_titles = sorted(list(all_relevant_titles)) 

    all_metrics = []
    
    # Initialisation des compteurs totaux pour les métriques Micro
    total_TP = 0
    total_FP = 0
    total_FN = 0
    
    # 2. Boucle d'évaluation
    for i, item in enumerate(evaluation_data):
        query = item["query"]
        relevant_docs = item["relevant_documents"]
        
        # *** APPEL AU MODÈLE : REMPLACEZ CETTE LIGNE ***
        retrieved_docs = placeholder_match_function(query) 
        # *** FIN DE L'APPEL ***
        
        # 3. Calcul des métriques
        metrics = evaluate_query(query, relevant_docs, retrieved_docs)
        all_metrics.append(metrics)
        
        # Mise à jour des totaux Micro
        total_TP += metrics["TP"]
        total_FP += metrics["FP"]
        total_FN += metrics["FN"]
        
        print(f"  [Q {i+1}/{len(evaluation_data)}] '{query[:50]}...' - P: {metrics['Precision']:.4f}, R: {metrics['Recall']:.4f}, F1: {metrics['F1-Score']:.4f}")


    # 4. Calcul des Métriques Globales (Macro et Micro)
    
    # Métriques Macro: Moyenne des métriques par requête
    avg_P_macro = sum(m["Precision"] for m in all_metrics) / len(all_metrics)
    avg_R_macro = sum(m["Recall"] for m in all_metrics) / len(all_metrics)
    avg_F1_macro = sum(m["F1-Score"] for m in all_metrics) / len(all_metrics)
    
    # Métriques Micro: Calcul basé sur l'agrégation des TP, FP, FN totaux
    avg_P_micro = total_TP / (total_TP + total_FP) if (total_TP + total_FP) > 0 else 0.0
    avg_R_micro = total_TP / (total_TP + total_FN) if (total_TP + total_FN) > 0 else 0.0
    avg_F1_micro = (2 * avg_P_micro * avg_R_micro) / (avg_P_micro + avg_R_micro) if (avg_P_micro + avg_R_micro) > 0 else 0.0

    print("\n" + "="*50)
    print(f"RÉSUMÉ DES RÉSULTATS (Cutoff K={CUTOFF_K})")
    print("="*50)
    
    print("\n--- Métriques Micro (Agrégation TP/FP/FN) ---")
    print(f"Total TP: {total_TP}, Total FP: {total_FP}, Total FN: {total_FN}")
    print(f"Précision (Micro): {avg_P_micro:.4f}")
    print(f"Rappel (Micro):    {avg_R_micro:.4f}")
    print(f"F1-Score (Micro):  {avg_F1_micro:.4f}")

    print("\n--- Métriques Macro (Moyenne par Requête) ---")
    print(f"Précision (Macro): {avg_P_macro:.4f}")
    print(f"Rappel (Macro):    {avg_R_macro:.4f}")
    print(f"F1-Score (Macro):  {avg_F1_macro:.4f}")
    
    print("\n" + "="*50)
    print("Évaluation terminée.")


if __name__ == "__main__":
    run_evaluation(EVALUATION_DATA_FILE)