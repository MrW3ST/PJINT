# PJINT — Pages Jaunes Intelligence

Outil d'extraction de données professionnelles depuis Pages Jaunes, avec interface web **et CLI**.

---

## Fonctionnalités

- Extraction automatique par ville + catégorie
- Données récupérées : nom, téléphone, adresse, catégorie
- Affichage en temps réel (Server-Sent Events)
- Total Pages Jaunes affiché dès la première page
- Progression en cours : page X / Y · N entrées
- Anti-boucle : détection automatique des doublons de pages
- Anti-détection : user-agent aléatoire, stealth JS, délais humains
- Pause / reprise : sauvegarde l'état dans le navigateur (localStorage)
- Historique des recherches (15 dernières, persistant)
- Export CSV / JSON / Excel / TXT
- Thème clair / sombre
- Avertissement si fermeture pendant un scraping en cours
- **CLI** : scraping et export directement en terminal

---

## Installation

```bash
pip install fastapi uvicorn playwright beautifulsoup4 lxml
playwright install chromium
# Optionnel : affichage enrichi en CLI et export Excel
pip install rich openpyxl
```

---

## Interface web

```bash
python app.py
```

L'interface s'ouvre automatiquement sur `http://localhost:8000`.

### Utilisation

1. Saisir une **ville** (ex: `Lyon`, `Paris 75001`)
2. Saisir ou sélectionner une **catégorie** dans la liste filtrée (ex: `plombier`, `association`)
3. Cliquer **[ EXTRAIRE ]** ou appuyer sur Entrée
4. Suivre la progression dans les cadres **EN COURS** et **TOTAL PJ**
5. À la fin, cliquer **⬇ EXPORTER** pour télécharger les données

### Pause / Reprise

- **[ PAUSE ]** : sauvegarde la page courante et tous les résultats, arrête le scraping
- Dans la sidebar, la recherche apparaît avec l'icône ⏸ en orange
- Cliquer dessus recharge les résultats et reprend depuis la page sauvegardée
- **[ STOP ]** : arrête définitivement et efface l'état de pause

### Catégories disponibles

La liste propose des catégories individuelles et des **groupes** (ex: `Toute la Restauration`, `Tous les Médecins`) qui lancent automatiquement plusieurs sous-recherches. Toute catégorie libre peut aussi être saisie directement.

---

## CLI

```bash
python cli.py --ville <ville> --keyword <catégorie> [options]
```

### Options

| Option | Alias | Description |
|--------|-------|-------------|
| `--ville` | `-v` | Ville à scraper (obligatoire) |
| `--keyword` | `-k` | Catégorie ou groupe (obligatoire) |
| `--output` | `-o` | Fichier de sortie (auto-généré si omis) |
| `--format` | `-f` | `csv` (défaut), `json`, `excel`, `txt` |
| `--fields` | | Colonnes à exporter : `nom,telephone,adresse,categorie` (toutes par défaut) |
| `--quiet` | `-q` | Désactive l'affichage de progression |
| `--list-groups` | | Affiche les groupes disponibles |

Le fichier de sortie est **toujours généré** — si `-o` est omis, le nom est auto-généré (`pjint_<ville>_<keyword>.<ext>`). La sauvegarde est **progressive** : chaque page est écrite immédiatement sur disque. En cas d'interruption (Ctrl+C, coupure réseau), les données déjà scrapées sont conservées.

### Exemples

```bash
# Scraping simple → pjint_lyon_plombier.csv généré automatiquement
python3 cli.py -v Lyon -k plombier

# Seulement les téléphones, un par ligne
python3 cli.py -v Angers -k association -f txt --fields telephone

# Nom + téléphone en CSV
python3 cli.py -v Paris -k "médecin généraliste" --fields nom,telephone -o medecins.csv

# Groupe complet → JSON
python3 cli.py -v Nantes -k __restauration -f json -o restaurants.json

# Groupe artisans → Excel
python3 cli.py -v Bordeaux -k __artisans -f excel -o artisans.xlsx

# Scraping long en arrière-plan (résiste à la fermeture du terminal)
nohup python3 cli.py -v Angers -k __tout -f txt --fields telephone > log.txt 2>&1 &
tail -f log.txt   # suivre la progression

# Voir les groupes disponibles
python3 cli.py --list-groups
```

### Groupes disponibles

| Identifiant | Description |
|-------------|-------------|
| `__restauration` | Toute la Restauration |
| `__alimentation` | Toute l'Alimentation |
| `__sante_medecin` | Tous les Médecins |
| `__sante_para` | Toute la Para-médecine |
| `__sante_etab` | Tous les Établissements de Santé |
| `__beaute` | Toute la Beauté |
| `__sport` | Tout le Sport |
| `__hotellerie` | Toute l'Hôtellerie |
| `__education` | Toute l'Éducation |
| `__informatique` | Tout l'Informatique |
| `__artisans` | Tous les Artisans |
| `__automobile` | Tout l'Automobile |
| `__commerce` | Tout le Commerce |
| `__services_pers` | Tous les Services à la Personne |
| `__liberales` | Toutes les Professions Libérales |
| `__immobilier` | Tout l'Immobilier |
| `__transport` | Tout le Transport |
| `__funeraire` | Tout le Funéraire |
| `__animaux` | Tous les Animaux |
| `__loisirs` | Tous les Loisirs |
| `__tout` | Toutes les catégories |

---

## Structure

```
PJINT/
├── scraper.py       # Logique de scraping (Playwright + parsing) — générateur async
├── app.py           # Serveur FastAPI (interface web, SSE)
├── cli.py           # Interface ligne de commande
├── static/
│   └── index.html   # Interface web complète (CSS + JS intégrés)
└── README.md
```

---

## Notes

- Les données extraites sont publiques (Pages Jaunes)
- À utiliser dans un cadre légal uniquement
- Pages Jaunes peut bloquer les requêtes trop fréquentes (Cloudflare) — en cas de blocage, attendre quelques minutes ou changer de réseau
- Le total annoncé par PJ est une estimation, le scraper s'arrête quand les pages ne retournent plus de nouveaux résultats
