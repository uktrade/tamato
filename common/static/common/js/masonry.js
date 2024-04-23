let timeout = null;

/**
 * Transforms the position of cards in a container in a masonry-layout fashion.
 */
const masonryLayout = () => {
  const container = document.getElementById("masonry-container");
  const cards = container.querySelectorAll(".masonry-card");

  // The desired gap between all cards in the container.
  const margin = parseInt(window.getComputedStyle(cards[0]).margin) * 2;

  const columns =
    container.offsetWidth / cards[0].offsetWidth >= 2 ? [0, 0] : [0];
  const columnWidth = container.offsetWidth / columns.length;

  let containerHeight = container.offsetHeight;
  container.style.position = "relative";
  container.style.height = containerHeight + "px";

  for (const card of cards) {
    const shortestColHeight = Math.min(...columns);
    const shortestColumn = columns.indexOf(shortestColHeight);

    // Position below the card in the shortest column with respect to `margin`.
    card.style.position = "absolute";
    card.style.top = shortestColHeight + "px";
    card.style.left = shortestColumn * columnWidth + "px";

    columns[shortestColumn] += card.offsetHeight + margin;
  }

  // Adjust for space saved.
  containerHeight -= containerHeight - Math.max(...columns);
  container.style.height = containerHeight + "px";
};

/**
 * Delays calls to `masonryLayout()` triggered by resize events to once every 200ms.
 */
const throttleMasonry = () => {
  const delay = 200;
  if (!timeout) {
    timeout = setTimeout(() => {
      masonryLayout();
      timeout = null;
    }, delay);
  }
};

/**
 * Sets up masonry layout for pages with a container comprising of cards.
 *
 * The container element must have `masonry-container` as an ID attribute.
 * And card elements must have `masonry-card` as a class attribute.
 */
const initMasonry = () => {
  const container = document.getElementById("masonry-container");
  if (container) {
    masonryLayout();

    // Ensure the layout remains responsive.
    window.addEventListener("resize", throttleMasonry);
  }
};

export { initMasonry };
