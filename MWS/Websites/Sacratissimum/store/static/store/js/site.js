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
