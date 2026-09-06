# API

Documentation interactive (Swagger/OpenAPI) : **http://localhost:8000/docs**
(générée automatiquement par FastAPI).

Toutes les routes sauf `/api/auth/login` et `/api/health` exigent un JWT :
`Authorization: Bearer <token>`.

## Authentification

| Méthode | Route | Description |
|---------|-------|-------------|
| POST | `/api/auth/login` | Échange email/mot de passe contre un JWT |
| GET | `/api/auth/me` | Profil de l'utilisateur courant |

Corps de login : `{"email": "...", "password": "..."}`.
Réponse : `{"access_token": "...", "token_type": "bearer", "user": {...}}`.

Rôles : `ADMIN`, `ANALYST`, `REVIEWER`, `USER` (RBAC).

## Documents

| Méthode | Route | Rôles | Description |
|---------|-------|-------|-------------|
| POST | `/api/documents/upload` | tous | Upload multipart (`file`) ; validation sécurité |
| GET | `/api/documents` | tous | Liste (filtre optionnel `status_filter`) |
| GET | `/api/documents/{id}` | tous* | Détail + analyse + dernière revue |
| GET | `/api/documents/{id}/file` | tous* | Fichier original (image/PDF) |
| DELETE | `/api/documents/{id}` | propriétaire/ADMIN | Suppression (fichier + métadonnées) |

\* *visibilité selon le rôle : un `USER` ne voit que ses documents.*

## Analyse

| Méthode | Route | Rôles | Description |
|---------|-------|-------|-------------|
| POST | `/api/documents/{id}/analyze` | ANALYST, ADMIN | Déclenche le pipeline complet |
| GET | `/api/documents/{id}/analysis` | tous* | Résultat d'analyse (PII incluses) |

Pipeline : prétraitement OpenCV → extraction Gemini (texte + confiances) →
détection PII + anonymisation → analyse Gemini (sentiment, émotions, catégorie,
mots-clés, résumé) → contrôle qualité → `COMPLETED` ou `REQUIRES_REVIEW`.

## Revue humaine

| Méthode | Route | Rôles | Description |
|---------|-------|-------|-------------|
| POST | `/api/documents/{id}/review` | REVIEWER, ADMIN | Corriger / valider / rejeter |

Corps : `{"corrected_text"?, "corrected_sentiment"?, "corrected_category"?,
"comment"?, "decision": "VALIDATED"|"REJECTED"}`.

## Dashboard

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/dashboard/statistics` | Totaux, sentiments, confiances moyennes, revues requises, derniers documents |

## Système

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/health` | Statut + connexion base |

## États d'un document

```
UPLOADED → VALIDATING → PREPROCESSING → OCR_PROCESSING → TEXT_EXTRACTED
→ ANALYZING → ANALYZED
    ├── COMPLETED
    └── REQUIRES_REVIEW → REVIEWED (ou FAILED si rejeté)
Erreur → FAILED (raison générique côté utilisateur, détails en logs)
```

## Codes d'erreur

| Code | Signification |
|------|---------------|
| 400 | Fichier refusé (type, taille, contenu…) |
| 401 | JWT manquant / invalide / expiré |
| 403 | Rôle insuffisant (RBAC) |
| 404 | Document introuvable ou non visible |
| 409 | État incompatible (document en cours, revue non autorisée) |
| 429 | Trop de requêtes (rate limiting) |
| 502 | Échec du pipeline d'analyse (message générique) |

Les réponses d'erreur ont la forme `{"detail": "..."}` — jamais de stack trace.