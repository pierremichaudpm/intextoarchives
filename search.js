// Recherche côté client, insensible aux accents et à la casse.
(function () {
  "use strict";
  var champ = document.getElementById("champ-recherche");
  if (!champ) return;

  function normaliser(s) {
    return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
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
