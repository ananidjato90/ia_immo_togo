# ImmoTogo AI

Pipeline Retrieval-Augmented Generation (RAG) francophone, bâtie sur le modèle `mistral-7b-instruct`, pour répondre aux requêtes immobilières portant sur des annonces togolaises (locations, ventes, achats d'appartements, maisons, bureaux, terrains, etc.).

## Sommaire

1. [Architecture](#architecture)
2. [Prérequis](#prérequis)
3. [Installation](#installation)
4. [Collecte des annonces](#collecte-des-annonces)
5. [Indexation & RAG](#indexation--rag)
6. [API FastAPI](#api-fastapi)
7. [Personnalisation du modèle](#personnalisation-du-modèle)
8. [Planification & monitoring](#planification--monitoring)
9. [Tests](#tests)
10. [Roadmap suggérée](#roadmap-suggérée)

## Architecture

- **Collecte** : des collecteurs asynchrones (Scraping, via `httpx` + `selectolax`) ciblent les portails immobiliers listés (CoinAfrique, ImmoOz, extensible à d'autres sites). Les annonces sont normalisées avec des `Enum` (type de bien, transaction) et enrichies (surface, prix, localisation, etc.).
- **Stockage** : PostgreSQL (ou toute base compatible SQLAlchemy) héberge les tables `listings` et `listing_chunks`. Les scripts `scripts/bootstrap_db.py` et `scripts/run_ingest.py` initialisent et alimentent la base.
- **Vecteurs** : les textes sont encodés via `sentence-transformers/all-MiniLM-L6-v2` et stockés dans une base `Chroma` persistée localement (`.chroma/`).
- **RAG** : `immotogo.pipeline.rag.RetrievalAugmentedGenerator` combine une recherche sémantique dans Chroma avec un appel au modèle Mistral (hébergé sur Hugging Face Inference) pour générer des réponses contextualisées.
- **API** : FastAPI expose `/search` et `/health`, orchestrés par `uvicorn` via `scripts/run_api.py`.

```
Collecteurs async -> Normalisation -> PostgreSQL -> Chroma -> RAG (Mistral) -> API
```

## Prérequis

- Python 3.10+
- PostgreSQL 14+ (ou service compatible `postgresql+psycopg`)
- Compte Hugging Face avec accès au modèle `mistralai/Mistral-7B-Instruct-v0.3`
- (Facultatif) GPU pour accélérer l'encodage ou un endpoint d'inférence externe pour Mistral

Variables d'environnement recommandées (`.env` à placer à la racine) :

```
POSTGRES_DSN=postgresql+psycopg://immotogo:immotogo@localhost:5432/immotogo
HF_TOKEN=hf_xxx
HF_MISTRAL_MODEL=mistralai/Mistral-7B-Instruct-v0.3
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENVIRONMENT=dev
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Créer la base de données :

```bash
createdb immotogo
psql -d immotogo -c "CREATE USER immotogo WITH PASSWORD 'immotogo';"
psql -d immotogo -c "GRANT ALL PRIVILEGES ON DATABASE immotogo TO immotogo;"
python scripts/bootstrap_db.py
```

## Collecte des annonces

Les collecteurs sont définis dans `immotogo.collectors.sites`. Pour lancer une collecte ponctuelle :

```bash
python scripts/run_ingest.py
```

Le script :
- récupère les annonces (limite 200 par collecteur par exécution);
- alimente PostgreSQL (upsert);
- génère les chunks et les enregistre dans Chroma.

### Ajouter un nouveau site

1. Créer un nouveau collecteur héritant de `BaseCollector` dans `immotogo/collectors/`.
2. Implémenter `collect()` en normalisant les champs.
3. Ajouter le collecteur à la liste `collect_all()`.

## Indexation & RAG

- Le module `immotogo.pipeline.ingest` gère l'upsert et la création de chunks.
- `immotogo.pipeline.embeddings` configure les embeddings Hugging Face et la base vectorielle.
- `immotogo.pipeline.rag` orchestre la recherche et prépare le prompt (instructions système + contexte structuré).

Pour tester la génération dans un shell Python :

```python
from immotogo.pipeline.rag import RetrievalAugmentedGenerator
from immotogo.data.schemas import ListingQuery

rag = RetrievalAugmentedGenerator()
response = rag.answer(ListingQuery(query="Je cherche un appartement meublé à louer à Lomé", max_results=5))
print(response.answer)
```

## API FastAPI

Lancer l'API en mode développement :

```bash
uvicorn immotogo.services.api:app --reload --port 8000
```

Requête exemple (POST `/search`) :

```bash
curl -X POST http://127.0.0.1:8000/search \
     -H "Content-Type: application/json" \
     -d '{"query": "Je cherche une maison à acheter à Kara", "max_results": 6}'
```

Réponse JSON (tronquée) :

```json
{
  "query": {"query": "Je cherche une maison à acheter à Kara", "max_results": 6, "require_structured": true},
  "answer": "Résumé de la meilleure annonce...",
  "listings": [ ... ],
  "used_chunks": [ ... ],
  "model_name": "mistralai/Mistral-7B-Instruct-v0.3",
  "generated_at": "2025-11-13T12:34:56"
}
```

## Personnalisation du modèle

- **Fine-tuning LoRA** : utilisez `peft` pour adapter Mistral sur des dialogues question/réponse générés à partir d'annonces togolaises.
- **Datasets synthétiques** : générer des scénarios multi-critères (budget, localisation, équipements) pour augmenter la robustesse.
- **Reranking** : intégrer un modèle de reranking (ex. `cross-encoder/ms-marco-MiniLM-L-6-v2`) avant l'appel RAG pour améliorer la pertinence.

## Planification & monitoring

- Orchestration via Airflow/Celery : planifier `scripts/run_ingest.py` toutes les 2-4 heures avec un throttle respectant les `robots.txt`.
- Logging & alerting : exporter les métriques (nombre d'annonces nouvelles, latence API, coût token Hugging Face).
- Conformité : respecter les CGU des sites, exposer un User-Agent descriptif, journaliser les demandes de retrait de données.

## Tests

```bash
pytest
```

Ajouter des tests d'intégration pour les collecteurs (mocks de réponses HTML) et des tests de charge pour l'API.

## Roadmap suggérée

- Intégrer progressivement les sites restants de la liste fournie.
- Ajouter une couche de géocodage (OpenStreetMap/Nominatim) pour enrichir les fiches.
- Mettre en place un pipeline d'évaluation automatique (BLEU/Rouge + validation métier).
- Déployer l'API derrière un Ingress sécurisé (HTTPS) et activer l'authentification JWT ou via clé API.

---

> **Note** : le dépôt contient du code prêt à exécuter mais certaines étapes (accès aux sites, tuning modèle, CI/CD) nécessitent encore des validations réglementaires et opérationnelles avant passage en production.
