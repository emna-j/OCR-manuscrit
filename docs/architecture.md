# Architecture — Secure Manuscript Intelligence Platform

> Document évolutif : mis à jour à chaque phase d'implémentation.

## 1. Vue d'ensemble

Application modulaire à trois couches : **frontend React**, **backend FastAPI**, et des **services externes** (Gemini, PostgreSQL, MinIO). Chaque étape du pipeline est un service isolé et testable.

```
                         ┌─────────────────────────┐
                         │        FRONTEND         │
                         │ React + TypeScript      │
                         │ Dashboard               │
                         └────────────┬────────────┘
                                      │
                                  HTTPS / JWT
                                      │
                         ┌────────────▼────────────┐
                         │       BACKEND API       │
                         │       FastAPI           │
                         └────────────┬────────────┘
                                      │
               ┌──────────────────────┼──────────────────────┐
               │                      │                      │
               ▼                      ▼                      ▼
       ┌───────────────┐      ┌──────────────┐      ┌───────────────┐
       │ File Security │      │ Preprocessing│      │ Authentication│
       │ Validation    │      │ OpenCV       │      │ JWT / RBAC    │
       └───────┬───────┘      └──────┬───────┘      └───────────────┘
               │                     │
               └──────────────┬──────┘
                              ▼
                     ┌──────────────────┐
                     │   Gemini VLM     │
                     │ Manuscript OCR   │
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ Structured Text  │
                     │ + Confidence     │
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ PII Detection    │
                     │ Anonymization    │
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ Text Analysis    │
                     │ Gemini           │
                     └────────┬─────────┘
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
         Sentiment         Emotion          Category
              │               │                │
              └───────────────┼────────────────┘
                              ▼
                     ┌──────────────────┐
                     │ Quality Control  │
                     │ Confidence       │
                     └────────┬─────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              High confidence      Low confidence
                    │                   │
                    ▼                   ▼
               Automatic          Human Review
                    │                   │
                    └─────────┬─────────┘
                              ▼
                     ┌──────────────────┐
                     │ PostgreSQL       │
                     │ Results / Logs   │
                     └──────────────────┘
```

## 2. Choix technologiques et compromis

| Choix | Justification | Compromis |
|-------|---------------|-----------|
| Gemini comme VLM unique | Modèle vision-langage le plus adapté à la transcription manuscrite multi-étapes | Dépendance externe ; coût/latence par document ; risque de changement de comportement du modèle |
| Backend FastAPI (Python) | Écosystème IA/vision (OpenCV, Pillow), typage Pydantic, OpenAPI/Swagger gratuit | GIL pour calcul lourd ; mitigé car le gros du calcul est côté Gemini |
| React + Vite + Tailwind | Frontend moderne, rapide, DX élevée | Nécessite une discipline de typage stricte pour rester maintenable |
| PostgreSQL pour métadonnées, MinIO pour fichiers | Séparation données structurées / binaires ; le stockage objet est le bon outil pour les images | Deux systèmes à opérer (résolu par Docker Compose) |
| Deux appels Gemini séparés (extraction puis analyse) | Frontières de responsabilité nettes ; prompts spécialisés et sécurisés | Coût et latence doublés par document |

## 3. Pipeline et états du document

Machine d'états :

```
UPLOADED → VALIDATING → PREPROCESSING → OCR_PROCESSING → TEXT_EXTRACTED
→ ANALYZING → ANALYZED
    ├── HIGH_CONFIDENCE → COMPLETED
    └── LOW_CONFIDENCE  → REQUIRES_REVIEW → REVIEWED

Erreur à tout moment → FAILED
```

- Le document est d'abord **validé** (extension, MIME, taille, contenu, nombre de pages, résolution).
- Ensuite **prétraité** (OpenCV) pour améliorer la reconnaissance.
- **Étape A — Extraction** : Gemini transcrit le manuscrit en JSON structuré avec scores de confiance par ligne.
- **Étape B — Analyse** : le texte extrait (anonymisé) est analysé pour sentiment / émotions / catégorie / mots-clés / résumé.
- **Contrôle qualité** : si `confiance OCR < seuil` ou `confiance analyse < seuil` → `REQUIRES_REVIEW` (Human-in-the-loop).
- Les seuils sont **configurables** et seront calibrés sur le dataset d'évaluation (Phase 14), pas présentés comme scientifiquement validés avant.

## 4. Sécurité

Voir aussi `docs/security.md` (complété en Phase 13). Principes structurants dès la conception :

1. **Prompt injection** — tout document est une donnée non fiable ; prompts système explicites interdisant de suivre les instructions du document ; sortie contrainte à du JSON strict.
2. **Data leakage** — seul le strict nécessaire est envoyé à Gemini ; le texte est anonymisé avant l'analyse.
3. **Excessive agency** — Gemini ne produit que du texte : aucun accès base de données, système de fichiers, shell ou outils.
4. **Hallucination** — scores de confiance, règles de cohérence, validation humaine en dessous des seuils.
5. **Secrets** — clé Gemini et secrets JWT uniquement côté backend, via variables d'environnement. `.env` ignoré par git.
6. **Logs** — structurés, sans clés, tokens, mots de passe ni contenu sensible complet (événements : LOGIN, UPLOAD, DOCUMENT_ANALYSIS, PII_DETECTION, AI_REQUEST, AI_RESPONSE_STATUS, HUMAN_REVIEW, DOCUMENT_DELETION).

## 5. Modèle de données (aperçu)

```
users
  └── documents            # métadonnées + état + statut validation
        └── document_analysis          # sentiment, émotions, catégorie, mots-clés, confiances
              ├── pii_detections       # type, emplacement, risque
              └── human_reviews        # corrections, validation, commentaire
audit_logs                    # traçabilité (événements ci-dessus)
```

Les fichiers binaires (originaux et prétraités) sont stockés dans MinIO, jamais en base. Une politique de rétention sera définie.

## 6. API (cible)

```
POST   /api/auth/login
POST   /api/documents/upload
GET    /api/documents
GET    /api/documents/{id}
POST   /api/documents/{id}/analyze
GET    /api/documents/{id}/analysis
POST   /api/documents/{id}/review
DELETE /api/documents/{id}
GET    /api/dashboard/statistics
```

Documentation interactive via Swagger/OpenAPI fournie par FastAPI (`/docs`).

## 7. Journal des décisions

| Date | Décision | Contexte |
|------|----------|----------|
| Phase 1 | Repository initialisé sur `main` ; structure issue de la section 25 du cahier des charges | Démarrage propre, phases progressives |
| Phase 1 | Seuils par défaut `OCR < 0.75` / `analyse < 0.70` déclarés provisoires | Doivent être évalués sur le dataset avant toute interprétation |