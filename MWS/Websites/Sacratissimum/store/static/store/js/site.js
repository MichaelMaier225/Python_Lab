(() => {
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('#site-nav');
  if (toggle && nav) {
    toggle.hidden = false;
    nav.classList.add('enhanced');
    const close = (focus = false) => {
      toggle.setAttribute('aria-expanded', 'false');
      nav.classList.remove('is-open');
      if (focus) toggle.focus();
    };
    toggle.addEventListener('click', () => {
      const open = toggle.getAttribute('aria-expanded') !== 'true';
      toggle.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('is-open', open);
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') close(true);
    });
    document.addEventListener('click', event => {
      if (!nav.contains(event.target) && !toggle.contains(event.target)) close();
    });
    nav.addEventListener('click', event => { if (event.target.closest('a')) close(); });
    window.matchMedia('(min-width: 761px)').addEventListener('change', () => close());
  }
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
  const controls = document.querySelector('.concept-controls');
  const concept = document.querySelector('#concept-image');
  if (controls && concept) {
    controls.hidden = false;
    controls.querySelectorAll('[data-concept]').forEach(button => {
      button.addEventListener('click', () => {
        concept.src = button.dataset.concept;
        concept.alt = button.dataset.alt;
        controls.querySelectorAll('[data-concept]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
        document.querySelector('#concept-color').textContent = button.dataset.label;
        document.querySelector('#concept-status').textContent = `Showing ${button.dataset.label}. Concept artwork, not real merchandise.`;
      });
    });
  }

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
