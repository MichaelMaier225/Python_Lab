(() => {
  document.querySelectorAll('[data-gallery-src]').forEach(link => {
    link.addEventListener('click', event => {
      const image = document.querySelector('#gallery-image');
      if (!image) return;
      event.preventDefault();
      image.src = link.dataset.gallerySrc;
      image.alt = link.dataset.galleryAlt;
      document.querySelectorAll('[data-gallery-src]').forEach(item => item.removeAttribute('aria-current'));
      link.setAttribute('aria-current', 'true');
      document.querySelector('#gallery-status').textContent = image.alt;
    });
  });
})();

// Progressive enhancements: every route and filter also works without JavaScript.
(() => {
  const topButton = document.querySelector('.back-to-top');
  if (topButton) {
    topButton.hidden = false;
    topButton.addEventListener('click', () => {
      window.scrollTo({top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
      const brand = document.querySelector('.site-header .brand');
      if (brand) brand.focus({preventScroll: true});
    });
  }

  const dialog = document.querySelector('.image-dialog');
  const expand = document.querySelector('.image-expand');
  if (dialog && expand && typeof dialog.showModal === 'function') {
    expand.hidden = false;
    expand.addEventListener('click', () => {
      const original = document.querySelector('.detail-image img');
      const enlarged = dialog.querySelector('img');
      enlarged.src = original.currentSrc || original.src;
      enlarged.alt = original.alt;
      dialog.querySelector('.dialog-caption').textContent = original.alt;
      dialog.showModal();
    });
    dialog.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
      if (event.target === dialog) {
        const bounds = dialog.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
      }
    });
  }

  const form = document.querySelector('[data-collection-form]');
  if (form && window.fetch && window.AbortController) {
    let timeout;
    let controller;
    let revision = 0;
    const status = document.querySelector('.filter-status');
    const update = async () => {
      const current = ++revision;
      clearTimeout(timeout);
      if (controller) controller.abort();
      controller = new AbortController();
      const url = new URL(form.action, window.location.origin);
      new FormData(form).forEach((value, key) => { if (value) url.searchParams.set(key, value); });
      document.querySelector('#collection-results').setAttribute('aria-busy', 'true');
      status.textContent = 'Updating the collection…';
      try {
        const response = await fetch(url, {signal: controller.signal});
        if (!response.ok) throw new Error('Collection request failed');
        const documentFragment = new DOMParser().parseFromString(await response.text(), 'text/html');
        const results = documentFragment.querySelector('#collection-results');
        if (!results) throw new Error('Collection response missing');
        if (current !== revision) return;
        document.querySelector('#collection-results').replaceWith(results);
        history.replaceState(null, '', url);
        status.textContent = results.querySelector('[role=status]').textContent;
      } catch (error) {
        if (error.name === 'AbortError' || current !== revision) return;
        status.textContent = 'Could not update the collection. Use Apply filters to reload the page.';
        document.querySelector('#collection-results').removeAttribute('aria-busy');
      }
    };
    form.querySelector('input[type=search]').addEventListener('input', () => {
      clearTimeout(timeout);
      // Invalidate any response that predates the latest keystroke.
      revision += 1;
      if (controller) controller.abort();
      document.querySelector('#collection-results').removeAttribute('aria-busy');
      timeout = setTimeout(update, 350);
    });
    form.querySelectorAll('select').forEach(select => select.addEventListener('change', update));
    // Apply remains a regular submit, providing a reliable fallback on failures.
    form.addEventListener('submit', () => { clearTimeout(timeout); if (controller) controller.abort(); });
  }
})();

// Native scroll snapping keeps the featured edit touch-friendly without a slider library.
(() => {
  const mobile = matchMedia('(max-width: 900px)');
  const rail = document.querySelector('.featured-products');
  const controls = document.querySelector('.collection-rail-controls');
  if (rail && controls) {
    const cards = [...rail.querySelectorAll('.product-card')];
    const previous = controls.querySelector('.rail-prev');
    const next = controls.querySelector('.rail-next');
    const position = controls.querySelector('.rail-position');
    let frame;
    let selected = -1;
    rail.tabIndex = 0;
    const step = () => cards.length > 1 ? cards[1].offsetLeft - cards[0].offsetLeft : rail.clientWidth;
    const update = () => {
      frame = null;
      const index = Math.max(0, Math.min(cards.length - 1, Math.round(rail.scrollLeft / step())));
      previous.disabled = index === 0;
      next.disabled = index === cards.length - 1;
      if (index !== selected) {
        position.textContent = `${index + 1} / ${cards.length}`;
        selected = index;
      }
    };
    const go = direction => {
      const index = Math.round(rail.scrollLeft / step());
      rail.scrollTo({
        left: Math.max(0, Math.min(cards.length - 1, index + direction)) * step(),
        behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
      });
    };
    previous.addEventListener('click', () => go(-1));
    next.addEventListener('click', () => go(1));
    rail.addEventListener('scroll', () => { if (!frame) frame = requestAnimationFrame(update); }, {passive: true});
    rail.addEventListener('keydown', event => {
      if (event.target !== rail || !mobile.matches) return;
      if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
        event.preventDefault();
        go(event.key === 'ArrowRight' ? 1 : -1);
      }
    });
    const resize = () => {
      controls.hidden = !mobile.matches || cards.length < 2;
      rail.tabIndex = mobile.matches ? 0 : -1;
      update();
    };
    mobile.addEventListener('change', resize);
    new ResizeObserver(resize).observe(rail);
    resize();
  }

  const options = document.querySelector('.filter-options');
  if (options) {
    const color = options.querySelector('[name=color]');
    const sort = options.querySelector('[name=sort]');
    const sync = () => {
      options.open = !mobile.matches || Boolean(color.value) || sort.value !== 'featured';
    };
    mobile.addEventListener('change', sync);
    sync();
  }

  const header = document.querySelector('.site-header');
  if (header) {
    let queued = false;
    const update = () => { header.classList.toggle('is-scrolled', scrollY > 16); queued = false; };
    window.addEventListener('scroll', () => { if (!queued) { queued = true; requestAnimationFrame(update); } }, {passive: true});
    update();
  }
})();
