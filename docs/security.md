# Sécurité

Ce document décrit les protections implémentées (cahier des charges §12-13, §17)
et les limites connues.

## 1. Authentification et autorisation

- **JWT** signé (HMAC-SHA256, `PyJWT`), secret uniquement dans la configuration
  (variable d'environnement / `.env`, jamais committé). Durée de vie configurable.
- **Mots de passe** hachés avec **bcrypt** (sel aléatoire). Jamais stockés en clair.
- **RBAC** : `ADMIN`, `ANALYST`, `REVIEWER`, `USER`.
  | Action | Rôles autorisés |
  |--------|-----------------|
  | Login / profil | public / tout utilisateur authentifié |
  | Upload | tout utilisateur authentifié |
  | Analyse (pipeline Gemini) | ANALYST, ADMIN |
  | Revue humaine | REVIEWER, ADMIN |
  | Suppression | propriétaire, ADMIN |
  | Lecture | propriétaire, ANALYST, REVIEWER, ADMIN |
- Un utilisateur simple ne voit **que ses documents** ; les autres rôles voient
  l'ensemble. Un document invisible renvoie **404** (pas de fuite d'existence).

## 2. Upload sécurisé (Phase 3)

Chaque fichier est validé avant stockage (`services/validation_service.py`) :
1. **extension** : liste blanche (PNG, JPG, JPEG, PDF) ;
2. **taille** : plafond configurable (10 Mo par défaut) ;
3. **contenu réel** : vérification des **octets magiques** (le MIME déclaré par
   le client n'est jamais fiable) + décodage PIL / ouverture PyMuPDF ;
4. **PDF** : nombre de pages plafonné (10) ;
5. **images** : résolution plafonnée (8000 px).

Les erreurs renvoient des messages génériques côté client ; les détails
techniques vont dans les logs sécurisés.

## 3. Protection contre les attaques IA

### Prompt injection
Le document est toujours traité comme une **donnée non fiable** :
- le prompt système d'extraction interdit explicitement de suivre les
  instructions du document et de révéler les instructions système ;
- le prompt d'analyse applique les mêmes règles au texte extrait ;
- réponse contrainte en **JSON** (`response_mime_type`), température 0,
  parsing défensif + validation Pydantic ;
- les tests vérifient la présence des règles dans les prompts (§ test_security.py).

### Data leakage
- Seule l'image (ou le texte) nécessaire est envoyée à Gemini ;
- le texte est **anonymisé avant l'analyse sémantique** (les PII sont
  remplacées par `[TYPE]`) ;
- la clé API Gemini n'existe que côté backend, jamais dans le frontend.

### Excessive agency
Gemini ne produit que du texte : **aucun accès** à la base de données, au
système de fichiers, au shell ou à des outils. Aucune action n'est déclenchée
par le contenu d'un document.

### Hallucination
- scores de confiance (OCR par ligne + global, analyse) ;
- contrôle qualité et **Human-in-the-loop** si un seuil n'est pas atteint
  (`REQUIRES_REVIEW`) — seuils configurables et non présentés comme validés ;
- règles de cohérence (sentiment valide, valeurs bornées 0-1).

## 4. API security

- **Rate limiting** : fenêtre glissante en mémoire (configurable). Renvoie 429.
  ⚠️ Limite connue : en mémoire → à remplacer par une solution partagée
  (Redis) en multi-instances.
- **CORS** : origines configurées en liste blanche.
- **Validation** : Pydantic sur toutes les entrées.
- **Erreurs** : jamais de stack trace renvoyée au client — messages génériques,
  détails dans les logs (handler global + tests dédiés).
- **Secrets** : masqués dans les logs (filtre sur `password=`, `token=`, `key=`,
  `authorization=`…). Tests vérifiant l'absence de fuite dans OpenAPI et les
  réponses.

## 5. Stockage

- Les binaires ne sont **jamais** stockés en base (PostgreSQL = métadonnées).
- Backends : `local` (développement) ou `MinIO` (docker/production), derrière
  une interface commune avec **anti path-traversal** sur les clés.
- La suppression d'un document retire l'objet du stockage et ses métadonnées
  (cascade). Une politique de rétention automatique reste à définir en
  production (versions MinIO / lifecycle).

## 6. Journalisation (audit)

Événements tracés (`audit_logs`) : LOGIN, UPLOAD, DOCUMENT_ANALYSIS,
PII_DETECTION, AI_REQUEST, AI_RESPONSE_STATUS, HUMAN_REVIEW, DOCUMENT_DELETION.
Jamais journalisés : clés API, mots de passe, tokens, contenu complet des
documents. Logs applicatifs structurés JSON (UTC ISO 8601) avec masquage.

## 7. Recommandations production

- **HTTPS** en terminaison (reverse proxy / load balancer).
- Rate limiting partagé (Redis) et par utilisateur en plus de l'IP.
- Rotation régulière des secrets (`JWT_SECRET_KEY`, clés stockage).
- Comptes administrateur nominatifs, jamais partagés.
- Sauvegardes chiffrées PostgreSQL + MinIO ; politique de rétention.
- Surveillance : Prometheus/Grafana suggérés (voir docs/architecture.md).