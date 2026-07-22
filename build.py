#!/usr/bin/env python3
"""Générateur de site statique pour inTexto Archives (archives d'intexto.ca).

Lit les articles Markdown (front matter YAML + paragraphes texte) dans
content/posts/ et produit un site statique complet dans dist/.

Usage :  python build.py          (depuis le répertoire archive-site/)
"""

import datetime
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import yaml
from jinja2 import Environment, select_autoescape

BASE_DIR = Path(__file__).resolve().parent
CONTENT_DIR = BASE_DIR / "content" / "posts"
DIST_DIR = BASE_DIR / "dist"

SITE_TITLE = "inTexto Archives"
SITE_TAGLINE = (
    "Archives du journal inTexto (intexto.ca), journal de la communauté "
    "haïtienne de Montréal, 2014–2026."
)
SITE_ACTUEL_URL = "https://www.intexto.ca/"
LOGO_SRC = BASE_DIR / "assets" / "intextologo2.png"

MOIS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


# ---------------------------------------------------------------- utilitaires

def slugify(texte: str) -> str:
    """Slug ASCII pour les URL d'auteurs (accents retirés)."""
    nfkd = unicodedata.normalize("NFKD", texte)
    ascii_ = nfkd.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")
    return slug or "inconnu"


def parser_date(valeur) -> datetime.date | None:
    """Accepte un datetime.date/datetime (PyYAML) ou une chaîne YYYY-MM-DD."""
    if valeur is None:
        return None
    if isinstance(valeur, datetime.datetime):
        return valeur.date()
    if isinstance(valeur, datetime.date):
        return valeur
    texte = str(valeur).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(texte, fmt).date()
        except ValueError:
            continue
    return None


def date_fr(d: datetime.date | None) -> str:
    if d is None:
        return "Date inconnue"
    return f"{d.day} {MOIS_FR[d.month - 1]} {d.year}"


# ------------------------------------------------------------------ lecture

def charger_articles():
    articles = []
    for chemin in sorted(CONTENT_DIR.glob("*.md")):
        texte = chemin.read_text(encoding="utf-8")
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", texte, re.DOTALL)
        if match:
            meta = yaml.safe_load(match.group(1)) or {}
            corps = match.group(2)
        else:
            meta, corps = {}, texte

        slug = str(meta.get("slug") or chemin.stem)
        date = parser_date(meta.get("date"))
        auteur = (meta.get("author") or "").strip() or None
        # Paragraphes séparés par des lignes vides ; certains fichiers
        # utilisent de simples retours à la ligne (un paragraphe par ligne).
        blocs = [p.strip() for p in re.split(r"\n\s*\n", corps) if p.strip()]
        if len(blocs) <= 1:
            paragraphes = [l.strip() for l in corps.splitlines() if l.strip()]
        else:
            paragraphes = [re.sub(r"\s*\n\s*", " ", b) for b in blocs]

        articles.append({
            "slug": slug,
            "titre": str(meta.get("title") or slug).strip(),
            "date": date,
            "date_iso": date.isoformat() if date else "",
            "date_fr": date_fr(date),
            "date_approx": meta.get("date_source") in ("wayback", "wayback_snapshot"),
            "auteur": auteur,
            "auteur_slug": slugify(auteur) if auteur else None,
            "url_source": meta.get("source_url") or "",
            "url_wayback": meta.get("wayback_url") or "",
            "extrait": bool(meta.get("excerpt_only")),
            "paragraphes": paragraphes,
        })

    # Plus récent d'abord ; les dates inconnues à la fin ;
    # tri déterministe sur le slug en cas d'égalité.
    articles.sort(key=lambda a: (a["date"] is None,
                                 -(a["date"] or datetime.date.min).toordinal(),
                                 a["slug"]))
    return articles


# ------------------------------------------------------------------ gabarits

CSS = """
/* Design aligné sur le nouveau intexto.ca (src/styles/App.css du site React) */
:root { --accent: #fc1a1d; --accent-clair: #f06b6b; --accent-fonce: #d44545;
  --bleu: #008bff; --texte: #1a1a1a; --texte-secondaire: #4a4a4a;
  --gris: #6c757d; --bordure: rgba(0,0,0,.1); --bordure-forte: rgba(0,0,0,.15);
  --ombre-sm: 0 1px 3px rgba(0,0,0,.06);
  --transition: all 0.25s ease; }
* { box-sizing: border-box; }
html { font-size: 100%; }
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, sans-serif;
  font-size: 16px; line-height: 1.6; color: var(--texte); background: #fff;
  margin: 0; padding: 0;
  -webkit-font-smoothing: antialiased;
}
h1, h2, h3 { font-family: 'Playfair Display', Georgia, 'Times New Roman',
  'Liberation Serif', serif; font-weight: 700; line-height: 1.2; }
p { line-height: 1.7; color: var(--texte-secondaire); }
a { color: var(--accent); text-decoration: none; transition: var(--transition); }
a:hover, a:focus { color: var(--accent-fonce); }

/* Bandeau plein largeur, calqué sur .main-header du site actuel */
header.site {
  position: sticky; top: 0; z-index: 1000; background: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,.05);
  border-bottom: 1px solid var(--bordure);
}
.bandeau {
  max-width: 1400px; margin: 0 auto; padding: .6rem 1.5rem;
  display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap;
}
h1.logo { margin: 0; line-height: 1; flex-shrink: 0; }
h1.logo a { display: inline-flex; align-items: center; gap: .5rem; }
h1.logo a:hover { text-decoration: none; }
h1.logo img { height: 40px; width: auto; display: block; }
h1.logo .mot-archives { font-family: 'Playfair Display', Georgia, serif;
  font-weight: 600; font-size: 1.5rem; color: var(--accent); }
/* Nav calquée sur .nav-links : majuscules, souligné rouge au survol */
nav.site { flex: 1; display: flex; gap: 2rem; justify-content: center; }
nav.site a {
  font-weight: 600; font-size: .9rem; text-transform: uppercase;
  letter-spacing: .05em; color: var(--texte);
  padding: .5rem 0; border-bottom: 2px solid transparent;
}
nav.site a:hover, nav.site a:focus { color: var(--accent);
  border-bottom-color: var(--accent); text-decoration: none; }
.actions-entete { display: flex; gap: .75rem; align-items: center; }
.recherche { padding: .5rem 1rem; font: inherit; font-size: .9rem;
  border: 1px solid var(--bordure); border-radius: 50px; width: 220px; }
.recherche:focus { outline: none; border-color: var(--accent); }
/* CTA externe calqué sur .newsletter-btn : pilule rouge */
.cta-site { padding: .5rem 1.25rem; background: var(--accent); color: #fff;
  border-radius: 50px; font-weight: 600; font-size: .85rem;
  white-space: nowrap; }
.cta-site:hover, .cta-site:focus { background: var(--accent-fonce);
  color: #fff; text-decoration: none; transform: translateY(-2px); }
.cta-court { display: none; }

/* Colonne de lecture */
.conteneur { max-width: 700px; margin: 0 auto; padding: 2rem 1rem 3rem; }
p.tagline { color: var(--gris); font-size: .95rem; margin: 0 0 2rem; }
h2.annee { font-size: 1.4rem; font-weight: 700; color: var(--accent);
  border-bottom: 1px solid var(--bordure);
  padding-bottom: .25rem; margin: 2.2rem 0 1rem; }
ul.articles { list-style: none; margin: 0; padding: 0; }
ul.articles li { margin: 0 0 1.1rem; }
/* Titres de liste calqués sur .content-card-title : Playfair, sombres */
ul.articles .titre { font-family: 'Playfair Display', Georgia, serif;
  font-size: 1.15rem; font-weight: 700; line-height: 1.35; color: var(--texte); }
ul.articles .titre:hover { color: var(--accent); text-decoration: none; }
ul.articles .meta { color: var(--gris); font-size: .85rem; }
ul.articles .meta .auteur { font-weight: 600; color: var(--texte); }
article.corps p { margin: 0 0 1.15rem; }
/* Titre d'article calqué sur .modal-title */
article h1.titre { font-size: 2rem; font-weight: 900; line-height: 1.2;
  margin: 0 0 1rem; color: var(--texte); }
/* Métas calquées sur .modal-meta */
p.meta { color: var(--gris); font-size: .95rem;
  margin: 0 0 1.5rem; padding-bottom: 1rem;
  border-bottom: 1px solid var(--bordure); }
p.meta .approx { font-style: italic; }
.avis-extrait { border: 1px solid var(--accent); border-left-width: 4px;
  background: #fff5f5; padding: .8rem 1rem; margin: 0 0 1.5rem;
  font-size: .95rem; color: var(--texte-secondaire); }
span.extrait { color: var(--gris); font-size: .85rem; font-style: italic; }
.lien-retour { font-size: .9rem; margin-bottom: 1.5rem; display: inline-block;
  font-weight: 600; }
.lien-original { border-top: 1px solid var(--bordure); margin-top: 2.5rem;
  padding-top: 1rem; font-size: .9rem; color: var(--gris); }
.cache { display: none !important; }
.resultats-vide { color: var(--gris); font-style: italic; }

/* Pied de page calqué sur .main-footer du site actuel */
footer.site { background: #fff; border-top: 1px solid var(--bordure);
  padding: 1.5rem 1.5rem 1rem; }
.pied-conteneur { max-width: 1400px; margin: 0 auto; }
.pied-grille { display: flex; justify-content: space-between; gap: 2rem;
  flex-wrap: wrap; align-items: flex-start; margin-bottom: 1rem; }
.pied-col img { height: 40px; width: auto; display: block; }
.pied-col .nom-site { font-family: 'Playfair Display', Georgia, serif;
  font-weight: 600; color: var(--accent); font-size: 1.05rem;
  margin-top: .35rem; }
.pied-col h3 { font-size: .9rem; font-weight: 600; margin: 0 0 .5rem; }
.pied-col p, .pied-col a { color: var(--gris); font-size: .85rem;
  line-height: 1.5; margin: 0 0 .25rem; }
.pied-col a { display: block; }
.pied-col a:hover { color: var(--accent); }
.pied-bas { text-align: center; padding-top: 1rem;
  border-top: 1px solid var(--bordure); color: var(--gris); font-size: .8rem; }
.pied-bas p { color: var(--gris); font-size: .8rem; margin: 0; }

@media (max-width: 768px) {
  nav.site { order: 3; flex-basis: 100%; justify-content: flex-start;
    gap: 1.25rem; }
  .recherche { flex: 1; width: auto; min-width: 0; max-width: calc(100% - 20px); }
  .actions-entete { flex: 1; }
  .cta-complet { display: none; }
  .cta-court { display: inline; }
}
@media print {
  header.site, .lien-retour, footer.site { display: none; }
  body { font-size: 11pt; }
  a { color: inherit; }
  .conteneur { padding: 0; }
}
"""

BASE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block titre %}{{ site_title }}{% endblock %}</title>
<meta name="description" content="{{ site_tagline }}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@400;600;700&display=swap">
<style>{{ css | safe }}</style>
</head>
<body>
<header class="site">
  <div class="bandeau">
    <h1 class="logo"><a href="{{ racine }}index.html"><img
      src="{{ racine }}assets/intextologo2.png" alt="inTexto" height="40"><span
      class="mot-archives">Archives</span></a></h1>
    <nav class="site">
      <a href="{{ racine }}index.html">Accueil</a>
      <a href="{{ racine }}auteurs.html">Auteurs</a>
      <a href="{{ racine }}index.html#annees">Années</a>
    </nav>
    <div class="actions-entete">
      {% block recherche %}{% endblock %}
      <a class="cta-site" href="{{ site_actuel_url }}" rel="noopener"><span class="cta-complet">Site actuel intexto.ca &rarr;</span><span class="cta-court">Site actuel</span></a>
    </div>
  </div>
</header>
<div class="conteneur">
<p class="tagline">{{ site_tagline }}</p>
<main>
{% block contenu %}{% endblock %}
</main>
</div>
<footer class="site">
  <div class="pied-conteneur">
    <div class="pied-grille">
      <div class="pied-col">
        <img src="{{ racine }}assets/intextologo2.png" alt="inTexto">
        <div class="nom-site">Archives</div>
      </div>
      <div class="pied-col">
        <h3>Navigation</h3>
        <a href="{{ racine }}index.html">Accueil</a>
        <a href="{{ racine }}auteurs.html">Auteurs</a>
        <a href="{{ racine }}index.html#annees">Années</a>
      </div>
      <div class="pied-col">
        <h3>Site actuel</h3>
        <a href="{{ site_actuel_url }}" rel="noopener">intexto.ca</a>
        <p>Articles récupérés depuis<br>
        <a href="https://web.archive.org/">archive.org</a></p>
      </div>
    </div>
    <div class="pied-bas">
      <p>&copy; 2026 inTexto Archives. Tous droits réservés.</p>
    </div>
  </div>
</footer>
{% block scripts %}{% endblock %}
</body>
</html>
"""

TPL_INDEX = """{% extends "base" %}
{% block titre %}{{ site_title }}{% endblock %}
{% block recherche %}
<input type="search" id="champ-recherche" class="recherche"
       placeholder="Rechercher…" aria-label="Rechercher un article">
{% endblock %}
{% block contenu %}
<p class="resultats-vide cache" id="aucun-resultat">Aucun article ne correspond à votre recherche.</p>
{% for annee, liste in groupes %}
<section class="groupe-annee" data-annee="{{ annee or 'sans-date' }}">
  <h2 class="annee"{% if loop.first %} id="annees"{% endif %}>{% if annee %}{{ annee }}{% else %}Date inconnue (articles récents, 2025–2026){% endif %}</h2>
  <ul class="articles">
    {% for a in liste %}
    <li data-slug="{{ a.slug }}">
      <a class="titre" href="posts/{{ a.slug }}.html">{{ a.titre }}</a>{% if a.extrait %} <span class="extrait">(extrait)</span>{% endif %}<br>
      <span class="meta">{{ a.date_fr }}{% if a.date_approx %} (date approximative){% endif %}{% if a.auteur %} — Par <span class="auteur">{{ a.auteur }}</span>{% endif %}</span>
    </li>
    {% endfor %}
  </ul>
</section>
{% endfor %}
{% endblock %}
{% block scripts %}<script src="search.js"></script>{% endblock %}
"""

TPL_ARTICLE = """{% extends "base" %}
{% block titre %}{{ a.titre }} — {{ site_title }}{% endblock %}
{% block contenu %}
<a class="lien-retour" href="../index.html">&larr; Retour aux articles</a>
<article>
  <h1 class="titre">{{ a.titre }}</h1>
  {% if a.extrait %}
  {% if a.date %}
  <p class="meta">Publié le {{ a.date_fr }} <span class="approx">(date relevée sur une page d’accueil ou de section archivée)</span></p>
  {% endif %}
  <p class="avis-extrait">Texte intégral non archivé — extrait provenant de
  l’index du site. Cet article récent (2025–2026) n’a pas été capturé par la
  Wayback Machine avant la disparition du site.</p>
  {% else %}
  <p class="meta">
    {% if a.auteur %}Par <strong>{% if a.auteur_slug %}<a href="../auteur/{{ a.auteur_slug }}.html">{{ a.auteur }}</a>{% else %}{{ a.auteur }}{% endif %}</strong> · {% endif %}Publié le {{ a.date_fr }}{% if a.date_approx %} <span class="approx">(date approximative)</span>{% endif %}
  </p>
  {% endif %}
  <div class="corps">
    {% for p in a.paragraphes %}<p>{{ p }}</p>
    {% endfor %}
  </div>
  {% if a.url_wayback %}
  <p class="lien-original"><a href="{{ a.url_wayback }}" rel="noopener">Voir l’original sur archive.org</a></p>
  {% endif %}
</article>
{% endblock %}
"""

TPL_AUTEURS = """{% extends "base" %}
{% block titre %}Auteurs — {{ site_title }}{% endblock %}
{% block contenu %}
<h2 class="annee">Auteurs</h2>
<ul class="articles">
  {% for au in auteurs %}
  <li>
    <a class="titre" href="auteur/{{ au.slug }}.html">{{ au.nom }}</a><br>
    <span class="meta">{{ au.articles|length }} article{% if au.articles|length > 1 %}s{% endif %}</span>
  </li>
  {% endfor %}
</ul>
{% endblock %}
"""

TPL_AUTEUR = """{% extends "base" %}
{% block titre %}{{ au.nom }} — {{ site_title }}{% endblock %}
{% block contenu %}
<a class="lien-retour" href="../auteurs.html">&larr; Retour aux auteurs</a>
<h2 class="annee">Articles de {{ au.nom }}</h2>
<ul class="articles">
  {% for a in au.articles %}
  <li>
    <a class="titre" href="../posts/{{ a.slug }}.html">{{ a.titre }}</a><br>
    <span class="meta">{{ a.date_fr }}{% if a.date_approx %} (date approximative){% endif %}</span>
  </li>
  {% endfor %}
</ul>
{% endblock %}
"""

TPL_ANNEE = """{% extends "base" %}
{% block titre %}Année {{ annee }} — {{ site_title }}{% endblock %}
{% block contenu %}
<a class="lien-retour" href="../index.html">&larr; Retour aux articles</a>
<h2 class="annee">Articles de {{ annee }}</h2>
<ul class="articles">
  {% for a in articles %}
  <li>
    <a class="titre" href="../posts/{{ a.slug }}.html">{{ a.titre }}</a>{% if a.extrait %} <span class="extrait">(extrait)</span>{% endif %}<br>
    <span class="meta">{{ a.date_fr }}{% if a.date_approx %} (date approximative){% endif %}{% if a.auteur %} — Par <span class="auteur">{{ a.auteur }}</span>{% endif %}</span>
  </li>
  {% endfor %}
</ul>
{% endblock %}
"""

TPL_404 = """{% extends "base" %}
{% block titre %}Page introuvable — {{ site_title }}{% endblock %}
{% block contenu %}
<h2 class="annee">Page introuvable</h2>
<p>La page demandée n’existe pas. Consultez la
<a href="{{ racine }}index.html">liste complète des articles</a>.</p>
{% endblock %}
"""

SEARCH_JS = """// Recherche côté client, insensible aux accents et à la casse.
(function () {
  "use strict";
  var champ = document.getElementById("champ-recherche");
  if (!champ) return;

  function normaliser(s) {
    return s.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase();
  }

  var index = [];
  var items = Array.prototype.slice.call(document.querySelectorAll("ul.articles li[data-slug]"));
  var groupes = Array.prototype.slice.call(document.querySelectorAll(".groupe-annee"));
  var vide = document.getElementById("aucun-resultat");

  fetch("search.json").then(function (r) { return r.json(); }).then(function (donnees) {
    donnees.forEach(function (d) {
      d._cle = normaliser(d.title + " " + (d.author || "") + " " + (d.date || ""));
    });
    index = donnees;
  }).catch(function () { /* recherche indisponible : la liste reste complète */ });

  champ.addEventListener("input", function () {
    var q = normaliser(champ.value.trim());
    var correspondances = null;
    if (q) {
      correspondances = {};
      index.forEach(function (d) {
        if (d._cle.indexOf(q) !== -1) correspondances[d.slug] = true;
      });
    }
    var visibles = 0;
    items.forEach(function (li) {
      var montrer = !correspondances || correspondances[li.getAttribute("data-slug")];
      li.classList.toggle("cache", !montrer);
      if (montrer) visibles++;
    });
    groupes.forEach(function (g) {
      var restant = g.querySelectorAll("li:not(.cache)").length;
      g.classList.toggle("cache", restant === 0);
    });
    if (vide) vide.classList.toggle("cache", visibles !== 0);
  });
})();
"""

ROBOTS = """User-agent: *
Allow: /
"""


# -------------------------------------------------------------------- build

def construire():
    articles = charger_articles()
    if not articles:
        sys.exit("Aucun article trouvé dans " + str(CONTENT_DIR))

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    (DIST_DIR / "posts").mkdir(parents=True)
    (DIST_DIR / "auteur").mkdir()
    (DIST_DIR / "annee").mkdir()

    from jinja2 import DictLoader
    env = Environment(
        loader=DictLoader({
            "base": BASE, "index": TPL_INDEX, "article": TPL_ARTICLE,
            "auteurs": TPL_AUTEURS, "auteur": TPL_AUTEUR,
            "annee": TPL_ANNEE, "404": TPL_404,
        }),
        autoescape=select_autoescape(default=True),
    )

    contexte = {"site_title": SITE_TITLE, "site_tagline": SITE_TAGLINE,
                "site_actuel_url": SITE_ACTUEL_URL, "css": CSS, "racine": ""}

    def rendre(gabarit, chemin, **kw):
        html = env.get_template(gabarit).render({**contexte, **kw})
        (DIST_DIR / chemin).write_text(html, encoding="utf-8")

    # Regroupement par année (les articles sont déjà triés récent -> ancien).
    groupes = []
    for a in articles:
        annee = a["date"].year if a["date"] else None
        if groupes and groupes[-1][0] == annee:
            groupes[-1][1].append(a)
        else:
            groupes.append((annee, [a]))

    rendre("index", "index.html", groupes=groupes)

    for a in articles:
        rendre("article", f"posts/{a['slug']}.html", a=a, racine="../")

    # Auteurs (triés par nom ; seuls les articles avec auteur connu).
    auteurs = {}
    for a in articles:
        if a["auteur"]:
            auteurs.setdefault(a["auteur_slug"],
                               {"nom": a["auteur"], "slug": a["auteur_slug"],
                                "articles": []})["articles"].append(a)
    liste_auteurs = sorted(auteurs.values(),
                           key=lambda au: unicodedata.normalize("NFKD", au["nom"]).lower())
    rendre("auteurs", "auteurs.html", auteurs=liste_auteurs)
    for au in liste_auteurs:
        rendre("auteur", f"auteur/{au['slug']}.html", au=au, racine="../")

    for annee, liste in groupes:
        if annee is not None:
            rendre("annee", f"annee/{annee}.html", annee=annee, articles=liste,
                   racine="../")

    rendre("404", "404.html")

    recherche = [{"slug": a["slug"], "title": a["titre"],
                  "author": a["auteur"] or "", "date": a["date_iso"]}
                 for a in articles]
    (DIST_DIR / "search.json").write_text(
        json.dumps(recherche, ensure_ascii=False, indent=1), encoding="utf-8")
    (DIST_DIR / "search.js").write_text(SEARCH_JS, encoding="utf-8")
    (DIST_DIR / "robots.txt").write_text(ROBOTS, encoding="utf-8")

    # Logo du bandeau (seul intextologo2.png est utilisé).
    (DIST_DIR / "assets").mkdir(exist_ok=True)
    if LOGO_SRC.exists():
        shutil.copy2(LOGO_SRC, DIST_DIR / "assets" / LOGO_SRC.name)
    else:
        print("Avertissement : logo introuvable ->", LOGO_SRC, file=sys.stderr)

    nb_pages = 2 + len(articles) + 1 + len(liste_auteurs) + len(groupes)
    print(f"OK : {len(articles)} articles, {len(liste_auteurs)} auteurs, "
          f"{sum(1 for g in groupes if g[0])} années -> {nb_pages} pages dans {DIST_DIR}")


if __name__ == "__main__":
    construire()
