# Secure Manuscript Intelligence Platform

Plateforme web professionnelle d'analyse de documents manuscrits basée sur un **Vision-Language Model (Gemini)** : extraction du texte, analyse sémantique (sentiment, émotions, catégorie, mots-clés), détection PII, scoring de confiance et validation humaine — le tout dans une architecture sécurisée, traçable et évaluable.

> L'objectif est de construire une véritable application IA sécurisée, pas une simple démonstration OCR.

## Pipeline

```
Document manuscrit → Upload sécurisé → Validation → Prétraitement (OpenCV)
→ Gemini VLM (extraction) → Normalisation → Détection PII → Anonymisation
→ Analyse (sentiment / émotions / catégorie / mots-clés) → Score de confiance
→ Contrôle qualité → Human-in-the-loop si nécessaire → Stockage sécurisé → Dashboard
```

## Technologies

| Couche     | Stack |
|------------|-------|
| Frontend   | React + TypeScript + Vite + Tailwind CSS + TanStack Query |
| Backend    | Python + FastAPI + Pydantic + SQLAlchemy |
| Données    | PostgreSQL (métadonnées) + MinIO (fichiers) |
| IA         | Gemini VLM (moteur d'extraction et d'analyse) |
| Infra      | Docker Compose (frontend, backend, postgres, minio) |

## Structure du repository

```
├── frontend/          # React + TypeScript + Vite
│   └── src/
│       ├── components/
│       ├── pages/           # Login, Dashboard, Upload, Détail, Human Review
│       ├── services/
│       ├── hooks/
│       ├── types/
│       └── utils/
├── backend/
│   ├── app/
│   │   ├── api/             # auth, documents, analysis, review
│   │   ├── core/            # config, security, logging
│   │   ├── models/          # user, document, analysis, audit_log
│   │   ├── schemas/         # validation Pydantic
│   │   ├── services/        # gemini, ocr, preprocessing, pii, sentiment, security
│   │   └── utils/
│   └── tests/               # unit / integration / security / évaluation
├── data/
│   ├── samples/             # documents manuscrits d'exemple
│   └── evaluation/          # dataset + ground truth
├── docs/                    # architecture, sécurité, évaluation, API
├── docker-compose.yml       # (Phase 15)
├── .env.example
└── README.md
```

## Phases d'implémentation

Le développement est volontairement progressif (voir `docs/architecture.md`).

| Phase | Contenu | Statut |
|-------|---------|--------|
| 1 | Initialisation du repository et architecture | ✅ |
| 2 | Backend FastAPI + PostgreSQL | ✅ |
| 3 | Upload sécurisé | ✅ |
| 4 | Prétraitement OpenCV | ✅ |
| 5 | Intégration Gemini VLM | ✅ |
| 6 | Extraction structurée du manuscrit | ✅ |
| 7 | Analyse sentiment / émotion / catégorie | ✅ |
| 8 | PII detection et anonymisation | ✅ |
| 9 | Confidence scoring + Human-in-the-loop | ✅ |
| 10 | Frontend | ✅ |
| 11 | Authentication / RBAC | ✅ |
| 12 | Logs / monitoring | ✅ |
| 13 | Tests de sécurité | ✅ |
| 14 | Évaluation IA | ⏳ run réel en attente du quota journalier (harnais ✅) |
| 15 | Dockerisation et documentation | ✅ |

> 75 tests backend (unitaires, intégration, sécurité), build frontend vérifié,
> intégration Gemini vérifiée sur appels réels. Voir `docs/evaluation.md` pour le
> statut exact de l'évaluation.

## Démarrage rapide

### Tout Docker (recommandé)

```bash
cp .env.example .env   # renseigner GEMINI_API_KEY, JWT_SECRET_KEY, ADMIN_*…
docker compose up --build
```

- Frontend : http://localhost:8080
- API / Swagger : http://localhost:8000/docs
- MinIO console : http://localhost:9001

### Développement local

```bash
# Backend (dans backend/)
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# PostgreSQL puis migration
cp ../.env.example ../.env && ../.env  # renseigner les secrets
# démarrer un PostgreSQL local ou : docker compose up -d postgres
alembic upgrade head
python -m app.seed                         # crée le compte admin (ADMIN_*)
uvicorn app.main:app --reload              # API sur http://localhost:8000

# Frontend (dans frontend/, autre terminal)
npm install
npm run dev                                # http://localhost:5173 (proxy /api)
```

### Tests

```bash
cd backend && .venv/Scripts/python -m pytest   # 75 tests (unitaires/intégration/sécurité)
cd frontend && npm run build                    # vérification TypeScript + build
```

### Évaluation IA

```bash
cd backend
.venv/Scripts/python scripts/generate_eval_dataset.py   # dataset synthétique
.venv/Scripts/python scripts/run_evaluation.py --delay 12  # expériences Gemini réelles
```

## Principes de sécurité (résumé)

- La clé Gemini ne vit **que** côté backend, en variable d'environnement — jamais dans le code ni le frontend.
- Tout contenu de document est traité comme une **donnée non fiable** (protection contre la prompt injection).
- Gemini n'a **jamais** accès direct à la base, au système de fichiers ni au shell (excessive agency).
- JWT + RBAC (ADMIN / ANALYST / REVIEWER / USER), rate limiting, CORS strict, pas de stack traces exposées.
- Seuils de confiance configurables ; en dessous → `REQUIRES_REVIEW` (Human-in-the-loop).
- Logs d'audit sans secrets ni contenu sensible complet.

## Documentation

- [Architecture](docs/architecture.md)
- [Sécurité](docs/security.md)
- [Évaluation IA](docs/evaluation.md)
- [API](docs/api.md)
- Swagger : http://localhost:8000/docs