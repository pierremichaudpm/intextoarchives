# inTexto Archives

Site statique d'archives du journal **inTexto**, journal de la communauté
haïtienne de Montréal (2014–2025). Ce site est **distinct du site actuel
intexto.ca** (relancé depuis sous une nouvelle forme) : la base de données
WordPress originale ayant été perdue, les articles ont été récupérés de la
[Wayback Machine](https://web.archive.org/) et convertis en fichiers Markdown.
Le site généré est en lecture seule, sans dépendance côté serveur, hébergeable
gratuitement sur Cloudflare Pages ou GitHub Pages.

L'identité visuelle reproduit celle du site actuel (code React de
`intexto-react`, voir `src/styles/App.css` et `src/components/layout/`) en
version statique simplifiée : polices Playfair Display (titres) et Inter
(texte) via Google Fonts, rouge de marque `#fc1a1d` (foncé `#d44545`), gris
`#6c757d`, bordures `rgba(0,0,0,.1)` ; bandeau plein largeur collant avec logo
`assets/intextologo2.png` + le mot « Archives », navigation en majuscules à
souligné rouge, bouton-pilule rouge « Site actuel » ; pied de page à trois
colonnes avec ligne de copyright.

## Structure des répertoires

```
archive-site/
├── build.py              # générateur de site statique (ce dépôt)
├── assets/
│   ├── intextologo2.png  # logo du bandeau (copié dans dist/assets/)
│   └── intextologo.png   # variante avec slogan (non utilisée)
├── content/
│   ├── posts/<slug>.md   # articles : front matter YAML + paragraphes texte
│   └── index.json        # métadonnées de tous les articles (référence)
└── dist/                 # site généré (à déployer ; recréé à chaque build)
    ├── index.html        # liste chronologique, regroupée par année, + recherche
    ├── posts/<slug>.html # une page par article
    ├── auteurs.html      # liste des auteurs
    ├── auteur/<nom>.html # articles par auteur
    ├── annee/<aaaa>.html # index par année
    ├── assets/intextologo2.png
    ├── search.json       # index de recherche (côté client)
    ├── search.js         # script de recherche (seul JavaScript du site)
    ├── robots.txt
    └── 404.html
```

### Format des articles (`content/posts/<slug>.md`)

```markdown
---
title: "Titre de l'article"
date: 2020-01-20            # AAAA-MM-JJ
date_source: article        # ou "wayback" si la date vient de l'URL archive.org
author: "Jean Numa Goudou"  # facultatif
slug: mon-slug
source_url: "https://www.intexto.ca/mon-slug/"
wayback_url: "https://web.archive.org/web/.../mon-slug/"
---

Paragraphes en texte brut, séparés par des lignes vides
(ou un paragraphe par ligne).
```

## Régénérer le site

Le générateur utilise l'environnement virtuel existant du projet
(`harvest/.venv`), avec `PyYAML` et `Jinja2` (déjà installés).

```bash
cd archive-site
../harvest/.venv/bin/python build.py
```

Le script efface puis recrée `dist/` en entier. Il suffit donc d'ajouter ou de
remplacer des fichiers dans `content/posts/` puis de relancer la commande.
Champs manquants gérés sans erreur : auteur absent (l'article n'apparaît pas
dans les pages d'auteurs), date absente (article classé sous « Sans date »),
`date_source: wayback` (mention « date approximative » affichée).

## Déploiement

Le contenu à publier est **uniquement** le dossier `dist/`.

### Cloudflare Pages (gratuit)

1. Pousser ce dépôt sur GitHub/GitLab, puis sur
   [dash.cloudflare.com](https://dash.cloudflare.com) → **Workers & Pages** →
   **Create** → **Pages** → **Connect to Git**.
2. Paramètres de build :
   - Build command : `../harvest/.venv/bin/python build.py`
     (ou plus simplement, sans CI : générer `dist/` en local et utiliser
     l'option **Direct Upload** avec `npx wrangler pages deploy dist`)
   - Build output directory : `archive-site/dist`
   - Root directory : `archive-site`
3. Domaine personnalisé : dans le projet Pages → **Custom domains** →
   ajouter `intexto.ca` (et `www.intexto.ca`). Si le domaine utilise déjà les
   serveurs DNS de Cloudflare, l'enregistrement est créé automatiquement ;
   sinon, changer les nameservers du domaine chez le registraire vers ceux
   indiqués par Cloudflare.

### GitHub Pages (gratuit)

1. Générer le site en local (`build.py`) et pousser le contenu de `dist/`
   sur la branche `gh-pages` (ou dans le dossier `docs/` de `main`) :
   ```bash
   cd archive-site && ../harvest/.venv/bin/python build.py
   git subtree push --prefix archive-site/dist origin gh-pages
   ```
   (ou configurer une GitHub Action qui exécute `build.py` puis publie
   `archive-site/dist` avec `actions/deploy-pages`).
2. Dans **Settings → Pages**, choisir la branche/dossier de publication.
3. Domaine personnalisé : ajouter un fichier `CNAME` contenant `intexto.ca`
   à la racine du site publié, puis chez le registraire/DNS :
   - `A` pour `intexto.ca` → les IP de GitHub Pages
     (185.199.108.153, .109.153, .110.153, .111.153) ;
   - `CNAME` pour `www.intexto.ca` → `<utilisateur>.github.io`.

Le fichier `404.html` à la racine de `dist/` est utilisé automatiquement
comme page d'erreur par Cloudflare Pages et GitHub Pages.
