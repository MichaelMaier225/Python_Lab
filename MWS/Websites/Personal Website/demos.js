'use strict';

// Fixed synthetic records only. No visitor data, network requests, or persistence.
(() => {
  const el = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const money = value => '$' + value.toLocaleString('en-US');
  const rowsInto = (body, rows, rowClass) => {
    body.replaceChildren(...rows.map(row => {
      const tr = el('tr');
      if (rowClass) tr.className = rowClass(row);
      row.forEach(value => tr.append(el('td', String(value))));
      return tr;
    }));
  };
  const statsInto = (container, stats) => {
    container.replaceChildren(...stats.map(([label, value]) => {
      const cell = el('div'); cell.append(el('span', label), el('strong', value)); return cell;
    }));
  };
  const download = (name, records) => {
    const csv = records.map(row => row.map(value => '"' + String(value).replaceAll('"', '""') + '"').join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = el('a'); link.href = url; link.download = name; document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const mini = document.querySelector('[data-mini-lab]');
  if (mini) {
    const raw = [['ab-101', 'blue  mug', '$12', 'Formatting'], ['AB-101', 'Blue Mug', '12.00', 'Repeated row'], ['cd-202', 'linen towel', '', 'Missing price']];
    const clean = [];
    const seenProducts = new Set();
    raw.forEach(([sku, name, price]) => {
      const normalizedSku = sku.toUpperCase();
      const normalizedName = name.trim().replace(/\s+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      const numericPrice = price ? Number(price.replace('$', '')) : null;
      const key = JSON.stringify([normalizedSku, normalizedName, numericPrice]);
      if (seenProducts.has(key)) return;
      seenProducts.add(key);
      clean.push([normalizedSku, normalizedName, numericPrice === null ? '—' : '$' + numericPrice.toFixed(2), numericPrice === null ? 'Needs review' : 'Standardized']);
    });
    const body = mini.querySelector('[data-mini-rows]');
    const button = mini.querySelector('[data-mini-clean]');
    const status = mini.querySelector('[data-mini-status]');
    const reset = () => {
      rowsInto(body, raw, () => 'row-issue');
      status.textContent = 'Inconsistent names. A repeated product. One missing price.';
      button.textContent = 'Clean up this file →'; button.disabled = false;
    };
    button.addEventListener('click', () => {
      rowsInto(body, clean, row => row[3] === 'Needs review' ? 'row-issue' : 'row-fixed');
      status.textContent = 'Names and SKUs standardized. One duplicate removed after review. Missing price flagged, not guessed.';
      button.textContent = 'File cleaned · 1 item needs review'; button.disabled = true;
    });
    mini.querySelector('[data-mini-reset]').addEventListener('click', reset);
    reset();
  }

  const tabs = [...document.querySelectorAll('[data-demo-tab]')];
  if (!tabs.length) return;
  const selectTab = (key, updateHash = false) => {
    if (!tabs.some(tab => tab.dataset.demoTab === key)) key = 'cleanup';
    tabs.forEach(tab => {
      const active = tab.dataset.demoTab === key;
      tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1;
      document.querySelector('#' + tab.getAttribute('aria-controls')).hidden = !active;
    });
    if (updateHash) history.replaceState(null, '', '#' + key);
  };
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => selectTab(tab.dataset.demoTab, true));
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (i + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (i + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault(); tabs[next].focus(); selectTab(tabs[next].dataset.demoTab, true);
    });
  });
  selectTab(location.hash.slice(1));
  window.addEventListener('hashchange', () => selectTab(location.hash.slice(1)));

  // Cleanup: rules are independent, so disabling standardization changes deduplication.
  const customers = [
    ['  Jamie Lee ', 'JAMIE@example.test'],
    ['Jamie Lee', 'jamie@example.test'],
    ['alex smith', 'alex@example.test'],
    ['Morgan Davis', 'morgan@example.test'],
    ['Morgan Davis', 'morgan@example.test'],
    ['Taylor Reed', ''],
    [' casey jones ', 'CASEY@example.test'],
    ['Riley Brooks', 'riley@example.test']
  ];
  const normalizeName = name => name.trim().replace(/\s+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  let cleanedCustomers = customers.map(row => [...row]);
  const format = document.querySelector('#fix-format');
  const duplicates = document.querySelector('#fix-duplicates');
  const cleanupBody = document.querySelector('#cleanup-rows');
  const renderCustomers = (records, original) => {
    rowsInto(cleanupBody, records.map(([name, email]) => [original ? '“' + name + '”' : name, email || '—', email ? (original ? 'Not checked' : 'Ready') : 'Missing email']), row => row[2] === 'Missing email' ? 'row-issue' : '');
  };
  const resetCleanup = () => {
    format.checked = true; duplicates.checked = true;
    cleanedCustomers = customers.map(row => [...row]);
    renderCustomers(cleanedCustomers, true);
    statsInto(document.querySelector('#cleanup-stats'), [['Input rows', 8], ['Output rows', 8], ['Missing emails', 1]]);
    document.querySelector('#cleanup-caption').textContent = 'Original sample records · spaces are visible in quotation marks';
    document.querySelector('#cleanup-status').textContent = 'Choose the rules, then apply the cleanup. Missing emails will be flagged for review.';
  };
  document.querySelector('#clean-data').addEventListener('click', () => {
    const normalized = customers.map(([name, email]) => format.checked ? [normalizeName(name), email.trim().toLowerCase()] : [name, email]);
    const seen = new Set();
    cleanedCustomers = normalized.filter(row => {
      if (!duplicates.checked) return true;
      const key = JSON.stringify(row);
      if (seen.has(key)) return false;
      seen.add(key); return true;
    });
    renderCustomers(cleanedCustomers, !format.checked);
    const removed = customers.length - cleanedCustomers.length;
    statsInto(document.querySelector('#cleanup-stats'), [['Input rows', 8], ['Output rows', cleanedCustomers.length], ['Duplicates removed', removed]]);
    document.querySelector('#cleanup-caption').textContent = 'Result using your selected rules';
    document.querySelector('#cleanup-status').textContent = `${format.checked ? 'Names and emails standardized.' : 'Original formatting kept.'} ${removed} exact duplicate${removed === 1 ? '' : 's'} removed. One missing email still needs a person to check it.`;
  });
  document.querySelector('#reset-data').addEventListener('click', resetCleanup);
  document.querySelector('#download-cleanup').addEventListener('click', () => download('mws-example-customers.csv', [['Name', 'Email', 'Review'], ...cleanedCustomers.map(([name, email]) => [name, email, email ? '' : 'Missing email'])]));
  resetCleanup();

  // Inventory: group by normalized identifiers and keep decisions explicit.
  const catalog = [
    { sku: 'AB-101', name: 'Blue Ceramic Mug, 12 oz', price: 12 },
    { sku: 'ab101', name: 'Mug - Blue Ceramic - 12oz', price: 12 },
    { sku: 'CD-202', name: 'Linen Tea Towel', price: 18 },
    { sku: 'CD202', name: 'Tea Towel, Linen', price: 20 },
    { sku: 'EF-303', name: 'Cotton Throw', price: null }
  ];
  rowsInto(document.querySelector('#inventory-rows'), catalog.map(item => [item.sku, item.name, item.price === null ? 'Missing' : money(item.price)]));
  document.querySelector('#inventory-check').addEventListener('click', () => {
    const output = document.querySelector('#inventory-results'); output.replaceChildren(); output.hidden = false;
    const groups = new Map();
    catalog.forEach(item => {
      const key = item.sku.toUpperCase().replace(/[^A-Z0-9]/g, '');
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    });
    const findings = [];
    groups.forEach(items => {
      if (items.length > 1) {
        const samePrice = new Set(items.map(item => item.price)).size === 1;
        findings.push({ title: samePrice ? 'Possible duplicate · ' + items.map(i => i.sku).join(' / ') : 'Price conflict · ' + items.map(i => i.sku).join(' / '), text: samePrice ? 'The normalized SKU and price match. The descriptions are similar. Check the source records before choosing whether they belong together.' : 'These records share a normalized SKU, but one says $18 and the other says $20. The tool cannot decide which price is correct.' });
      }
    });
    catalog.filter(item => item.price === null).forEach(item => findings.push({ title: 'Missing price · ' + item.sku, text: 'This product has no price. Confirm it against the source before preparing an import. No price has been filled in.' }));
    findings.forEach((finding, i) => {
      const card = el('div', undefined, 'review-card');
      const label = el('label', 'Your review decision');
      const decision = el('select'); decision.setAttribute('aria-label', 'Review decision for ' + finding.title);
      [['', 'Still needs review'], ['source', 'Check with the source'], ['keep', 'Keep the records separate'], ['reviewed', 'Reviewed for this example']].forEach(([value, name]) => {
        const option = el('option', name); option.value = value; decision.append(option);
      });
      label.append(decision); card.append(el('h4', String(i + 1).padStart(2, '0') + ' / ' + finding.title), el('p', finding.text), label);
      decision.addEventListener('change', () => {
        card.classList.toggle('reviewed', decision.value === 'reviewed');
        const pending = [...output.querySelectorAll('select')].filter(select => select.value !== 'reviewed').length;
        document.querySelector('#inventory-result').textContent = `${findings.length} issues flagged. ${pending} still awaiting review. No records have been changed or removed.`;
      });
      output.append(card);
    });
    document.querySelector('#inventory-result').textContent = `${findings.length} issues flagged: a possible duplicate, a price conflict, and a missing price. Pick a review decision for each. No records removed.`;
  });

  // Automation: real transformations of two different input schemas.
  const storeExport = [
    { Product: 'Mugs', Quantity: 12, Price: 12 },
    { Product: 'Towels', Quantity: 8, Price: 18 },
    { Product: 'Bowls', Quantity: 6, Price: 16 }
  ];
  const onlineExport = [
    { Item: 'Mugs', Units: 8, 'Unit price': 12 },
    { Item: 'Towels', Units: 7, 'Unit price': 18 },
    { Item: 'Throws', Units: 5, 'Unit price': 40 }
  ];
  let workflowSummary = [];
  document.querySelector('#run-workflow').addEventListener('click', () => {
    const aligned = [...storeExport.map(row => ({ product: row.Product, units: row.Quantity, price: row.Price })), ...onlineExport.map(row => ({ product: row.Item, units: row.Units, price: row['Unit price'] }))];
    const grouped = new Map();
    aligned.forEach(row => {
      if (!grouped.has(row.product)) grouped.set(row.product, { product: row.product, units: 0, sales: 0 });
      const total = grouped.get(row.product); total.units += row.units; total.sales += row.units * row.price;
    });
    workflowSummary = [...grouped.values()];
    document.querySelectorAll('#pipeline li').forEach(item => item.classList.add('done'));
    rowsInto(document.querySelector('#workflow-rows'), workflowSummary.map(row => [row.product, row.units, money(row.sales)]));
    statsInto(document.querySelector('#workflow-stats'), [['Input rows', aligned.length], ['Products', grouped.size], ['Total sales', money(workflowSummary.reduce((n, row) => n + row.sales, 0))]]);
    document.querySelector('#workflow-result').hidden = false;
    document.querySelector('#workflow-status').textContent = 'Both column formats aligned. Six rows combined into four product totals. The summary below was calculated from the sample exports; review it before using it.';
  });
  document.querySelector('#reset-workflow').addEventListener('click', () => {
    document.querySelectorAll('#pipeline li').forEach(item => item.classList.remove('done'));
    document.querySelector('#workflow-result').hidden = true;
    document.querySelector('#workflow-rows').replaceChildren(); workflowSummary = [];
    document.querySelector('#workflow-status').textContent = 'Without a utility, you’d repeat these steps each time the exports arrive.';
  });
  document.querySelector('#download-report').addEventListener('click', () => download('mws-example-sales-summary.csv', [['Product', 'Units', 'Sales'], ...workflowSummary.map(row => [row.product, row.units, row.sales])]));

  const sales = [
    { month: 'October', name: 'Mugs', category: 'Kitchen', units: 20, price: 12 },
    { month: 'October', name: 'Towels', category: 'Home', units: 15, price: 18 },
    { month: 'October', name: 'Bowls', category: 'Kitchen', units: 10, price: 16 },
    { month: 'October', name: 'Throws', category: 'Home', units: 5, price: 40 },
    { month: 'November', name: 'Mugs', category: 'Kitchen', units: 26, price: 12 },
    { month: 'November', name: 'Towels', category: 'Home', units: 12, price: 18 },
    { month: 'November', name: 'Bowls', category: 'Kitchen', units: 14, price: 16 },
    { month: 'November', name: 'Throws', category: 'Home', units: 8, price: 40 }
  ];
  const renderSales = () => {
    const category = document.querySelector('#sales-filter').value;
    const month = document.querySelector('#month-filter').value;
    const selected = sales.filter(row => (category === 'all' || row.category === category) && (month === 'all' || row.month === month));
    const total = selected.reduce((n, row) => n + row.units * row.price, 0);
    const units = selected.reduce((n, row) => n + row.units, 0);
    const grouped = new Map();
    selected.forEach(row => grouped.set(row.name, (grouped.get(row.name) || 0) + row.units * row.price));
    const sorted = [...grouped].sort((a, b) => b[1] - a[1]);
    document.querySelector('#sales-total').textContent = money(total);
    document.querySelector('#sales-units').textContent = units;
    document.querySelector('#sales-top').textContent = sorted[0][0];
    const chart = document.querySelector('#sales-chart'); chart.replaceChildren();
    sorted.forEach(([name, value]) => {
      const bar = el('div', undefined, 'sales-bar');
      const track = el('div', undefined, 'bar-track'); const fill = el('span', undefined, 'bar-fill');
      fill.style.width = value / 552 * 100 + '%'; track.append(fill);
      bar.append(el('span', name), track, el('strong', money(value))); chart.append(bar);
    });
    rowsInto(document.querySelector('#sales-rows'), selected.map(row => [row.month, row.name, row.category, row.units, money(row.units * row.price)]));
    document.querySelector('#sales-insight').textContent = `${sorted[0][0]} lead this selection with ${money(sorted[0][1])} in sales. This view includes ${selected.length} sample records. Change the filters to see a different part of the same data.`;
  };
  document.querySelector('#sales-filter').addEventListener('change', renderSales);
  document.querySelector('#month-filter').addEventListener('change', renderSales);
  renderSales();

  const productPairs = {
    same: { a: 'Blue Ceramic Mug — 12 oz', b: 'Mug, Ceramic, Blue, 12oz' },
    size: { a: 'Blue Ceramic Mug — 12 oz', b: 'Mug, Ceramic, Blue, 16oz' },
    missing: { a: 'Blue Ceramic Mug — 12 oz', b: 'Blue Mug' }
  };
  const attributes = title => {
    const text = title.toLowerCase().replace(/(\d+)\s*oz/g, '$1oz');
    return { Type: /\bmug\b/.test(text) ? 'Mug' : null, Material: /\bceramic\b/.test(text) ? 'Ceramic' : null, Color: /\bblue\b/.test(text) ? 'Blue' : null, Size: text.match(/\b\d+oz\b/)?.[0] || null };
  };
  const renderPair = () => {
    const pair = productPairs[document.querySelector('#match-example').value];
    const output = document.querySelector('#match-pair'); output.replaceChildren();
    [['SUPPLIER A', pair.a], ['SUPPLIER B', pair.b]].forEach(([label, title]) => {
      const card = el('div'); card.append(el('small', label), el('h4', title)); output.append(card);
    });
    document.querySelector('#match-attributes').replaceChildren();
    document.querySelector('#match-result').textContent = 'Compare the actual attributes before deciding what belongs together.';
  };
  document.querySelector('#match-example').addEventListener('change', renderPair);
  document.querySelector('#match-products').addEventListener('click', () => {
    const pair = productPairs[document.querySelector('#match-example').value];
    const a = attributes(pair.a); const b = attributes(pair.b);
    const rows = Object.keys(a).map(key => [key, a[key] || 'Not supplied', b[key] || 'Not supplied', !a[key] || !b[key] ? 'Needs information' : a[key] === b[key] ? 'Matches' : 'Different']);
    const scroll = el('div', undefined, 'table-scroll'); const table = el('table');
    table.append(el('caption', 'Attribute comparison for this pair'));
    const thead = el('thead'); const headings = el('tr'); ['Attribute', 'Supplier A', 'Supplier B', 'Result'].forEach(label => { const th = el('th', label); th.scope = 'col'; headings.append(th); }); thead.append(headings);
    const tbody = el('tbody'); rowsInto(tbody, rows, row => row[3] === 'Matches' ? 'attribute-match' : 'attribute-different'); table.append(thead, tbody); scroll.append(table);
    document.querySelector('#match-attributes').replaceChildren(scroll);
    const different = rows.some(row => row[3] === 'Different'); const missing = rows.some(row => row[3] === 'Needs information');
    document.querySelector('#match-result').textContent = different ? 'Do not merge these records based on the name: the sizes differ. A 12oz mug and a 16oz mug should be reviewed as separate variants.' : missing ? 'Not enough information. The second record has no material or size. Ask for those details before deciding whether it matches.' : 'Potential match: type, material, color, and size all agree. Confirm brand and product identifiers before merging; matching attributes alone do not prove it is the same item.';
  });
  renderPair();
})();
