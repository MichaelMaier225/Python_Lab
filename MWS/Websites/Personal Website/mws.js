'use strict';
(() => {
  document.body.classList.add('js-ready');
  const config = window.MWS_CONFIG;
  const make = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const menu = document.querySelector('.menu');
  const nav = document.querySelector('#nav');
  menu.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && nav.classList.contains('open')) {
      nav.classList.remove('open'); menu.setAttribute('aria-expanded', 'false'); menu.focus();
    }
  });
  const current = location.pathname.split('/').pop() || 'index.html';
  nav.querySelectorAll('a').forEach(a => { if (a.getAttribute('href') === current) a.setAttribute('aria-current', 'page'); });
  document.querySelector('#year').textContent = new Date().getFullYear();
  const enabled = config.foundingOffer.enabled;
  document.querySelectorAll('[data-offer]').forEach(node => { node.hidden = !enabled; });
  document.querySelectorAll('[data-offer-status]').forEach(node => {
    node.textContent = enabled ? 'Introductory pricing is available subject to confirmed eligibility and offer availability.' : 'The introductory offer is closed. Regular starting prices apply to new quotes.';
  });
  document.querySelectorAll('[data-services]').forEach(grid => {
    const full = grid.dataset.services === 'full';
    config.services.forEach((service, i) => {
      const card = make('article', undefined, 'service-card');
      card.id = service.id;
      const overview = full ? make('div', undefined, 'service-overview') : card;
      const top = make('div', undefined, 'service-top');
      const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      icon.setAttribute('viewBox', '0 0 32 32');
      icon.setAttribute('fill', 'none');
      icon.setAttribute('stroke', 'currentColor');
      icon.setAttribute('stroke-width', '1.6');
      icon.setAttribute('aria-hidden', 'true');
      const paths = [
        'M5 7h22v19H5zM5 13h22M13 7v19M18 19l3 3 6-7',
        'M16 3 28 9v14l-12 6-12-6V9zM4 9l12 6 12-6M16 15v14',
        'M5 10h19l-4-4m4 4-4 4M27 22H8l4 4m-4-4 4-4',
        'M5 27h23M8 22v-7h4v7M16 22V9h4v13M24 22V4h4v18',
        'M8 9h16M9 10l7 13m7-13-7 13M5 6h6v6H5zM21 6h6v6h-6zM13 22h6v6h-6z'
      ];
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', paths[i]); icon.append(path);
      top.append(make('span', String(i + 1).padStart(2, '0'), 'service-number'), icon);
      overview.append(
        top,
        make('h3', service.name),
        make('p', service.summary)
      );
      const price = make('p', undefined, 'price');
      price.append(make('small', 'STARTING AT'));
      if (enabled) price.append(make('del', '$' + service.regular));
      price.append(make('strong', '$' + (enabled ? service.intro : service.regular)));
      price.append(make('small', enabled ? 'Founding client price · Regular from $' + service.regular : 'Regular starting price'));
      const link = make('a', full ? 'Request a Quote →' : 'Explore this service →', 'text-link');
      link.href = full ? 'contact.html?service=' + encodeURIComponent(service.id) : 'services.html#' + service.id;
      overview.append(price, link);
      if (full) {
        const detail = make('div', undefined, 'service-detail');
        const list = values => {
          const ul = make('ul');
          values.forEach(value => ul.append(make('li', value)));
          return ul;
        };
        const uses = make('details');
        uses.append(make('summary', 'Example uses'), list(service.examples));
        const extras = make('details');
        extras.append(make('summary', 'What needs a custom quote?'), make('p', service.custom));
        detail.append(make('h4', 'Base package'), list(service.scope), uses, extras);
        card.append(overview, detail);
      }
      grid.append(card);
    });
  });
  const form = document.querySelector('#quote-form');
  if (form) {
    const select = form.elements.service;
    config.services.forEach(s => { const option = make('option', s.name); option.value = s.name; select.append(option); });
    const requested = config.services.find(s => s.id === new URLSearchParams(location.search).get('service'));
    if (requested) select.value = requested.name;
    form.addEventListener('submit', event => {
      event.preventDefault(); if (!form.reportValidity()) return;
      const fields = new FormData(form);
      const text = ['Hello Maier Web Solutions,', '', ...[['Name', 'name'], ['Business', 'business'], ['Email', 'email'], ['Service', 'service'], ['Dataset size', 'size'], ['Preferred contact', 'contact'], ['Problem description', 'description']].map(([label, key]) => label + ': ' + (String(fields.get(key)).trim() || 'Not provided')), '', 'Please contact me about a free quote.'].join('\n');
      document.querySelector('#email-copy').value = text;
      document.querySelector('#open-email').href = 'mailto:maierwebsolutions@gmail.com?subject=' + encodeURIComponent('MWS quote request') + '&body=' + encodeURIComponent(text);
      document.querySelector('#email-result').hidden = false;
      document.querySelector('#quote-status').textContent = 'Request prepared. Review it below, then open your email app or copy it. Nothing has been sent.';
    });
    document.querySelector('#copy-request').addEventListener('click', async () => {
      const output = document.querySelector('#email-copy');
      try { await navigator.clipboard.writeText(output.value); document.querySelector('#quote-status').textContent = 'Request copied. Paste it into an email to maierwebsolutions@gmail.com.'; }
      catch { output.focus(); output.select(); document.querySelector('#quote-status').textContent = 'Select and copy the request below, then paste it into your email.'; }
    });
    form.querySelector('#quote-fields').disabled = false;
  }

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  document.querySelectorAll('.faq-question').forEach(button => {
    const answer = document.getElementById(button.getAttribute('aria-controls'));
    button.setAttribute('aria-expanded', 'false');
    answer.hidden = true;
    button.addEventListener('click', () => {
      const open = button.getAttribute('aria-expanded') !== 'true';
      button.setAttribute('aria-expanded', String(open));
      answer.hidden = !open;
      if (open && !reducedMotion.matches && answer.animate) {
        answer.animate([{ opacity: .3, transform: 'translateY(-5px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 180, easing: 'ease-out' });
      }
    });
  });

  // One-time entrances: content is visible by default and motion is never required.
  if (!reducedMotion.matches && 'IntersectionObserver' in window && Element.prototype.animate) {
    const entrance = node => node.animate(
      [{ opacity: .25, transform: 'translateY(22px)' }, { opacity: 1, transform: 'translateY(0)' }],
      { duration: 460, easing: 'cubic-bezier(.2,.7,.3,1)' }
    );
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entrance(entry.target); observer.unobserve(entry.target);
      });
    }, { threshold: .12 });
    document.querySelectorAll('.hero-copy, .hero-demo, .section-heading, .service-card, .steps article, .lab-feature .split, .about-band .split, .faq-item, .final-cta').forEach(node => observer.observe(node));
    reducedMotion.addEventListener('change', event => {
      if (!event.matches) return;
      observer.disconnect();
      document.getAnimations().forEach(animation => animation.cancel());
    });
  }
})();
