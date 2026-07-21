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
    "haïtienne de Montréal, 2014–2026. Site d’archives en lecture seule, "
    "reconstitué à partir de la Wayback Machine."
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
            "date_approx": meta.get("date_source") == "wayback",
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
:root { --accent: #fc1a1d; --accent-fonce: #d44545; --bleu: #008bff;
  --texte: #1a1a1a; --gris: #6c757d; --bordure: rgba(0,0,0,.1); }
* { box-sizing: border-box; }
html { font-size: 100%; }
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, sans-serif;
  line-height: 1.7; color: var(--texte); background: #fff;
  margin: 0; padding: 0 1rem;
}
.conteneur { max-width: 700px; margin: 0 auto; padding: 2rem 0 4rem; }
h1, h2 { font-family: 'Playfair Display', Georgia, 'Times New Roman',
  'Liberation Serif', serif; }
a { color: var(--accent); text-decoration: none; }
a:hover, a:focus { color: var(--accent-fonce); text-decoration: underline; }
header.site { border-bottom: 1px solid var(--bordure); padding-bottom: 1.25rem;
  margin-bottom: 2rem; }
h1.logo { margin: 0 0 .5rem; line-height: 1; }
h1.logo a { display: inline-flex; align-items: baseline; gap: .5rem;
  color: inherit; }
h1.logo a:hover { text-decoration: none; }
h1.logo img { height: 40px; width: auto; display: block;
  align-self: center; }
h1.logo .mot-archives { font-family: 'Playfair Display', Georgia, serif;
  font-weight: 600; font-size: 1.6rem; color: var(--accent); }
header.site p.tagline { color: var(--gris); font-size: .95rem; margin: 0 0 .75rem; }
p.site-actuel { font-size: .9rem; margin: 0 0 .75rem; }
nav.site { font-size: .95rem; margin-bottom: .75rem; }
nav.site a { margin-right: 1rem; }
.recherche { width: 100%; max-width: 22rem; padding: .45rem .6rem;
  font: inherit; border: 1px solid var(--bordure); border-radius: 3px; }
h2.annee { font-size: 1.4rem; font-weight: 600; color: var(--accent);
  border-bottom: 1px solid var(--bordure);
  padding-bottom: .25rem; margin: 2.2rem 0 1rem; }
ul.articles { list-style: none; margin: 0; padding: 0; }
ul.articles li { margin: 0 0 1.1rem; }
ul.articles .titre { font-size: 1.08rem; font-weight: 500; }
ul.articles .meta { color: var(--gris); font-size: .88rem; }
article.corps p { margin: 0 0 1.15rem; }
article h1.titre { font-size: 1.8rem; font-weight: 700; line-height: 1.3;
  margin: 0 0 .5rem; }
p.meta { color: var(--gris); font-size: .95rem; margin: 0 0 2rem; }
p.meta .approx { font-style: italic; }
.avis-extrait { border: 1px solid var(--accent); border-left-width: 4px;
  background: #fff5f5; padding: .8rem 1rem; margin: 0 0 1.5rem;
  font-size: .95rem; }
span.extrait { color: var(--gris); font-size: .85rem; font-style: italic; }
.lien-retour { font-size: .92rem; margin-bottom: 1.5rem; display: block; }
.lien-original { border-top: 1px solid var(--bordure); margin-top: 2.5rem;
  padding-top: 1rem; font-size: .9rem; color: var(--gris); }
footer.site { border-top: 1px solid var(--bordure); margin-top: 3rem;
  padding-top: 1rem; color: var(--gris); font-size: .85rem; }
.cache { display: none !important; }
.resultats-vide { color: var(--gris); font-style: italic; }
@media print {
  nav.site, .recherche, .lien-retour, .site-actuel, footer.site { display: none; }
  body { background: #fff; font-size: 11pt; }
  a { color: inherit; }
  h1.logo img { height: 28px; }
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
<div class="conteneur">
<header class="site">
  <h1 class="logo"><a href="{{ racine }}index.html"><img
    src="{{ racine }}assets/intextologo2.png" alt="inTexto" height="40"><span
    class="mot-archives">Archives</span></a></h1>
  <p class="tagline">{{ site_tagline }}</p>
  <p class="site-actuel"><a href="{{ site_actuel_url }}" rel="noopener">Visiter le site actuel intexto.ca &rarr;</a></p>
  <nav class="site">
    <a href="{{ racine }}index.html">Articles</a>
    <a href="{{ racine }}auteurs.html">Auteurs</a>
    <a href="{{ racine }}index.html#annees">Années</a>
  </nav>
  {% block recherche %}{% endblock %}
</header>
<main>
{% block contenu %}{% endblock %}
</main>
<footer class="site">
  <p>inTexto Archives — articles récupérés depuis
  <a href="https://web.archive.org/">archive.org</a> · Site actuel :
  <a href="{{ site_actuel_url }}" rel="noopener">intexto.ca</a></p>
</footer>
</div>
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
      <span class="meta">{{ a.date_fr }}{% if a.date_approx %} (date approximative){% endif %}{% if a.auteur %} — Par {{ a.auteur }}{% endif %}</span>
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
  <p class="avis-extrait">Texte intégral non archivé — extrait provenant de
  l’index du site. Cet article récent (2025–2026) n’a pas été capturé par la
  Wayback Machine avant la disparition du site.</p>
  {% else %}
  <p class="meta">
    Publié le {{ a.date_fr }}{% if a.date_approx %} <span class="approx">(date approximative)</span>{% endif %}{% if a.auteur %}<br>
    Par {% if a.auteur_slug %}<a href="../auteur/{{ a.auteur_slug }}.html">{{ a.auteur }}</a>{% else %}{{ a.auteur }}{% endif %}{% endif %}
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
    <a class="titre" href="../posts/{{ a.slug }}.html">{{ a.titre }}</a><br>
    <span class="meta">{{ a.date_fr }}{% if a.date_approx %} (date approximative){% endif %}{% if a.auteur %} — Par {{ a.auteur }}{% endif %}</span>
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
