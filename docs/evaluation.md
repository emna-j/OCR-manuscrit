# Évaluation IA

> **Avertissement** : les chiffres de cette page proviennent d'expériences **réellement
> exécutées**. Aucun résultat n'est inventé. Le dataset actuel est **synthétique**
> (texte rendu avec une police manuscrite puis dégradé) : il ne préjuge pas des
> performances sur de vrais manuscrits et ne constitue pas une validation scientifique.

## Harnais d'évaluation

| Composant | Emplacement | État |
|-----------|-------------|------|
| Métriques CER / WER / classification | `backend/app/evaluation/metrics.py` | ✅ testé unitairement (10 tests) |
| Dataset synthétique (8 documents) | `data/evaluation/samples/` + `ground_truth.json` | ✅ généré |
| Générateur de dataset | `backend/scripts/generate_eval_dataset.py` | ✅ |
| Exécution réelle des expériences | `backend/scripts/run_evaluation.py` | ✅ (prêt) |
| Résultats bruts | `data/evaluation/results.json` | généré par chaque run |

Cas couverts par le dataset (cahier des charges §19) : écriture lisible,
écriture difficile (inclinaison + bruit + flou), image inclinée, faible qualité,
bruit, textes courts et longs, plusieurs registres (réclamation, compliment,
note, demande), PII dans le texte.

## Exécution du 2026-09-06 (validation réelle, 2 documents)

Le quota **journalier** du compte free tier Google AI Studio (20 requêtes/jour
pour `gemini-3.6-flash`) a été atteint pendant la mise en place. Une validation
de bout en bout a néanmoins été **réellement exécutée** sur 2 documents (voir
`backend/scripts/smoke_gemini.py`) :

| id | Texte attendu | Texte extrait | CER | Sentiment (réel → prédit) |
|----|---------------|---------------|-----|---------------------------|
| smoke_1 | « Bonjour, ceci est un document de test manuscrit. » | identique | 0.000 | neutral → neutral |
| smoke_2 | « Je suis très satisfait du service, merci beaucoup ! » | identique | 0.000 | positive → positive |

Confiance OCR constatée : 0.99. Ces deux échantillons utilisent une police
imprimée (Arial) : la qualité est donc attendue comme élevée et **ne reflète pas**
la difficulté de l'écriture manuscrite réelle.

## Statut de l'évaluation complète

⚠️ **En attente** : le run complet sur les 8 documents du dataset nécessite
16 appels Gemini. Le quota journalier free tier étant épuisé le 2026-09-06,
l'exécution est à relancer après réinitialisation :

```bash
cd backend
.venv/Scripts/python scripts/run_evaluation.py --delay 12
```

Le script écrit `data/evaluation/results.json` et régénère cette page
(`docs/evaluation.md`) avec les métriques **réellement mesurées** :

- OCR : CER moyen, WER moyen ;
- classification : accuracy, precision, recall, F1 (macro et pondérée),
  matrice de confusion ;
- opérationnel : taux de revue (seuils configurés), taux d'erreurs critiques
  (sentiment faux), latence moyenne, tokens consommés.

Le coût moyen par document n'est pas estimé ici : il dépend de la tarification
du modèle et du volume, et ne serait pas mesuré mais supposé.

## Seuils de confiance

Les seuils par défaut (`OCR < 0.75`, `analyse < 0.70`) sont **provisoires**.
Ils ne seront considérés comme raisonnablement calibrés qu'après évaluation sur
un dataset représentatif (vrais manuscrits inclus) — voir `docs/architecture.md`.