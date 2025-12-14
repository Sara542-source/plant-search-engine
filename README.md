# 🌿 FOLIA : Moteur de Recherche Botanique

## 🌿 Introduction

Le projet **FOLIA** est une plateforme de recherche documentaire spécialisée, conçue pour interroger un corpus technique et scientifique couvrant la botanique, l'horticulture et la science des sols. L'objectif principal est de surmonter les limitations des moteurs de recherche traditionnels basés sur la simple correspondance de mots-clés. Pour cela, notre approche repose sur une double stratégie : une modélisation vectorielle robuste basée sur le TF-IDF et l'intégration de techniques d'intelligence linguistique pour interpréter le sens et les relations entre les termes. Le moteur est ainsi capable de gérer efficacement la terminologie scientifique complexe, les concepts clés et les entrées multilingues (notamment l'arabe), garantissant un haut niveau de pertinence.

## 🌿 Modélisation et Stratégies de Classement

Le classement des documents repose sur la modélisation vectorielle Term Frequency-Inverse Document Frequency (TF-IDF). Les documents et les requêtes sont convertis en vecteurs, et le score de pertinence est calculé via la **Similarité Cosinus**. Le projet a évolué en testant et comparant l'efficacité de trois modèles de représentation sémantique : 

### 1. Modèles de Représentation Sémantique Testés

Afin d'identifier la meilleure performance et de capturer la richesse sémantique du corpus botanique, trois modèles principaux ont été évalués :

* **Modèle Vectoriel (TF-IDF) :** Ce modèle sert de référence. Il utilise le calcul TF-IDF classique, où la pertinence repose sur la fréquence des termes. C'est la base de notre architecture optimisée.
* **Analyse Sémantique Latente (LSA) :** Une technique de réduction de dimensionnalité qui tente de découvrir les relations sémantiques entre les termes et les documents. Elle est efficace pour gérer la synonymie et la polysémie.
* **Word2Vec :** Un modèle d'apprentissage profond pour la représentation des mots (Word Embeddings). Il capture la sémantique contextuelle des mots, permettant de trouver des documents qui n'utilisent aucun terme de la requête, mais des synonymes contextuels.

### 2. Stratégies de Classement (Appliquées au Modèle Vectoriel Optimisé)

Notre architecture finale est une version optimisée du Modèle Vectoriel (TF-IDF), utilisant une approche en cascade avec les stratégies suivantes :

* **Modèle 1 : Pondération Intelligente (Optimisation de la Précision) :** Cette méthode vise principalement à améliorer la **Précision** du Top K en priorisant les termes les plus spécifiques. Les termes reconnus comme des **N-grams scientifiques** (ex: *Nigella sativa*) ou des **concepts clés** reçoivent un facteur de *boost* significatif. Inversement, les termes trop génériques (après lemmatisation) sont soumis à un facteur de *déboost* pour minimiser le bruit.
* **Modèle 2 : Expansion Sémantique (Optimisation du Rappel et Fallback) :** Ce mécanisme de *fallback* augmente le **Rappel**. Il exploite un **Thésaurus** et une table de **Lookup** pour identifier les synonymes et les termes plus généraux. Ces termes d'expansion sont ajoutés à la requête initiale et reçoivent un facteur de *boost* élevé, permettant de récupérer des documents utilisant une terminologie différente mais sémantiquement équivalente à celle de l'utilisateur.

## 🌿 Intégration et Enrichissement de la Plateforme (RAG & YouTube)

Le moteur de recherche **FOLIA** ne se contente pas de classer les documents. Il fait partie d'une architecture plus large visant à enrichir l'expérience utilisateur et à offrir des réponses synthétiques.

* **Retrieval-Augmented Generation (RAG) :** Notre moteur joue le rôle d'étape de *Retrieval* (récupération). Les fragments de documents les plus pertinents (les "chunks") sont extraits du corpus et sont ensuite transmis à un Modèle de Langage (LLM) pour générer une réponse synthétique et factuelle. Cela permet d'offrir des résumés précis au lieu d'une simple liste de liens.
* **Intégration de l'API YouTube :** Pour enrichir la plateforme avec du contenu multimédia et dynamique, nous avons intégré l'API YouTube. Cette intégration permet d'associer des requêtes de recherche à des vidéos pertinentes, offrant un support visuel aux informations textuelles techniques (ex: démonstration de techniques de taille, conditions de culture).

## 🌿 Prétraitement Linguistique

Un processus rigoureux de prétraitement est appliqué à la requête avant l'indexation et la recherche afin d'assurer la normalisation des termes : 

* **Lemmatisation Avancée :** L'outil linguistique **spaCy** est utilisé pour réduire les mots à leur lemme, regroupant toutes les variations grammaticales (ex: "planté", "plantes" $\rightarrow$ "plante").
* **Protection des N-Grams :** Avant la lemmatisation, un mécanisme isole et protège les N-grams scientifiques ou techniques pré-identifiés (ex: "Lawsonia inermis") pour conserver leur sémantique composée.
* **Gestion Multilingue (Arabe) :** Le moteur intègre une étape de normalisation spécifique pour les tokens arabes pour améliorer la correspondance avec les noms de plantes ou de concepts traditionnels.

## 🌿 Ressources Sémantiques et Indexation

Le moteur s'appuie sur une collection de ressources spécialisées stockées dans le répertoire `docs/` pour alimenter ses algorithmes de pondération et d'expansion :

* **Index Inversé :** Le cœur structurel du système, qui cartographie chaque terme unique du corpus aux identifiants des documents qui le contiennent et à sa fréquence d'apparition.
* **Thésaurus et Table de Lookup :** Ces fichiers fournissent les relations hiérarchiques et de synonymie indispensables à l'expansion sémantique du Modèle 2.
* **Listes de Concepts Protégés :** Ces listes définissent les ensembles de termes (scientifiques, concepts clés) qui sont ciblés par les facteurs de *boost* dans le Modèle 1, permettant un contrôle précis de la pertinence.
