'use strict';
(() => {
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
    config.services.forEach((service, i) => {
      const full = grid.dataset.services === 'full';
      const card = make('article', undefined, 'service-card'); card.id = service.id;
      card.append(make('span', String(i + 1).padStart(2, '0') + ' / MWS', 'service-number'), make('h3', service.name), make('p', service.summary));
      const price = make('p', undefined, 'price');
      price.append(make('small', 'STARTING AT'));
      if (enabled) price.append(make('del', '$' + service.regular));
      price.append(make('strong', '$' + (enabled ? service.intro : service.regular)));
      price.append(make('small', enabled ? 'Founding client price · Regular from $' + service.regular : 'Regular starting price'));
      card.append(price);
      if (full) {
        for (const [heading, values] of [['Example uses', service.examples], ['Base package', service.scope]]) {
          card.append(make('h4', heading)); const list = make('ul'); values.forEach(value => list.append(make('li', value))); card.append(list);
        }
        card.append(make('h4', 'Custom quote required'), make('p', service.custom));
      }
      const link = make('a', full ? 'Request a Quote ↗' : 'Explore this service →', 'text-link');
      link.href = full ? 'contact.html?service=' + encodeURIComponent(service.id) : 'services.html#' + service.id;
      card.append(link); grid.append(card);
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
  }
  const cleanupRows = document.querySelector('#cleanup-rows');
  if (cleanupRows) {
    const raw = [['  Jamie Lee ', 'JAMIE@example.test', ''], ['Jamie Lee', 'jamie@example.test', ''], [' alex smith', '', 'Missing email']];
    const render = rows => { cleanupRows.replaceChildren(...rows.map(row => { const tr = make('tr'); row.forEach(value => tr.append(make('td', value || '—'))); return tr; })); };
    render(raw);
    document.querySelector('#clean-data').addEventListener('click', () => {
      const seen = new Set(); const clean = raw.map(([name, email, note]) => [name.trim().replace(/\b\w/g, c => c.toUpperCase()), email.trim().toLowerCase(), note]).filter(row => { const key = JSON.stringify(row); if (seen.has(key)) return false; seen.add(key); return true; });
      render(clean); document.querySelector('#cleanup-caption').textContent = 'Standardized synthetic records';
      document.querySelector('#cleanup-status').textContent = '3 input rows → 2 output rows. One normalized duplicate removed; one missing email flagged, not invented.';
    });
    document.querySelector('#reset-data').addEventListener('click', () => { render(raw); document.querySelector('#cleanup-caption').textContent = 'Original synthetic records'; document.querySelector('#cleanup-status').textContent = 'Original records restored.'; });
    document.querySelector('#inventory-check').addEventListener('click', () => {
      const normalize = sku => sku.toUpperCase().replace(/[^A-Z0-9]/g, '');
      const candidate = normalize('AB-101') === normalize('ab101');
      document.querySelector('#inventory-result').textContent = candidate ? 'Potential duplicate: AB-101 and ab101 share normalized SKU AB101. Suggested format: AB-101; product name: Blue Ceramic Mug, 12 oz. Review source records before merging. No records removed.' : 'No candidate found.';
    });
    document.querySelector('#workflow-toggle').addEventListener('click', event => {
      const output = document.querySelector('#workflow-result'); output.hidden = !output.hidden;
      event.currentTarget.setAttribute('aria-pressed', String(!output.hidden));
      event.currentTarget.textContent = output.hidden ? 'Show Automated Workflow' : 'Hide Automated Workflow';
    });
    const sales = [{name:'Mugs',category:'Kitchen',units:20,price:12},{name:'Towels',category:'Home',units:15,price:18},{name:'Bowls',category:'Kitchen',units:10,price:16},{name:'Throws',category:'Home',units:5,price:40}];
    const source = document.querySelector('#sales-rows');
    sales.forEach(s => { const tr = make('tr'); [s.name,s.category,s.units,'$'+s.units*s.price].forEach(value => tr.append(make('td', value))); source.append(tr); });
    const renderSales = () => {
      const category = document.querySelector('#sales-filter').value;
      const selected = sales.filter(s => category === 'all' || s.category === category);
      document.querySelector('#sales-total').textContent = '$' + selected.reduce((n,s) => n+s.units*s.price,0).toLocaleString('en-US');
      document.querySelector('#sales-units').textContent = selected.reduce((n,s) => n+s.units,0);
      const chart = document.querySelector('#sales-chart'); chart.replaceChildren();
      selected.forEach(s => { const bar = make('div', undefined, 'sales-bar'); const value = s.units*s.price; const fill = make('span','$'+value); fill.style.width = (value/270*100)+'%'; bar.append(make('div',s.name),fill); chart.append(bar); });
    };
    document.querySelector('#sales-filter').addEventListener('change', renderSales); renderSales();
    document.querySelector('#match-products').addEventListener('click', () => {
      const tokens = value => value.toLowerCase().replace(/(\d+)\s*oz/g,'$1oz').replace(/[^a-z0-9]+/g,' ').trim().split(/\s+/).sort().join('|');
      const match = tokens('Blue Ceramic Mug — 12 oz') === tokens('Mug, Ceramic, Blue, 12oz');
      document.querySelector('#match-result').textContent = match ? 'Potential match: both records contain blue, ceramic, mug, and 12oz after normalization. Human review required; no automatic merge.' : 'Different normalized attributes; review required.';
    });
  }
})();
