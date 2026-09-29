(function () {
  const search = document.querySelector("[data-module-search]");
  const category = document.querySelector("[data-module-category]");
  const cards = Array.from(document.querySelectorAll("[data-module-card]"));
  const count = document.querySelector("[data-module-count]");

  if (!search || !category || !cards.length) return;

  function normalize(value) {
    return value.toLocaleLowerCase("nb-NO").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/æ/g, "ae").replace(/ø/g, "o").replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
  }

  function update() {
    const query = normalize(search.value);
    const selectedCategory = category.value;
    let visible = 0;

    cards.forEach(function (card) {
      const matchesText = !query || normalize(card.dataset.search).includes(query);
      const matchesCategory = !selectedCategory || card.dataset.category === selectedCategory;
      const show = matchesText && matchesCategory;
      card.hidden = !show;
      if (show) visible += 1;
    });

    count.textContent = visible + (visible === 1 ? " modul" : " moduler") + " funnet";
  }

  search.addEventListener("input", update);
  category.addEventListener("change", update);
  update();
}());