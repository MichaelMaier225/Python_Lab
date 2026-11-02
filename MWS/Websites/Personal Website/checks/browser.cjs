const {chromium}=require(process.env.MWS_PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
(async()=>{
 const outputDir=process.env.MWS_ARTIFACT_DIR || await fs.mkdtemp(path.join(os.tmpdir(),'mws-checks-'));
 await fs.mkdir(outputDir,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.MWS_BROWSER || '/usr/bin/chromium',args:['--no-sandbox']});
 const context=await browser.newContext();const page=await context.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.MWS_BASE_URL || 'http://127.0.0.1:8000/';
 const files=['index.html','services.html','examples.html','about.html','contact.html','terms.html','privacy.html'];
 let requests=0;
 page.on('response',r=>{if(r.status()>=400)errors.push(r.status()+' '+r.url());});
 for(const width of [1440,1024,768,390,320]){
  await page.setViewportSize({width,height:960});
  for(const file of files){
   assert.equal((await page.goto(base+file)).status(),200);requests++;
   await page.evaluate(async()=>{await Promise.all([document.fonts.load('600 18px Manrope'),document.fonts.load('italic 400 48px \"Instrument Serif\"')]);await document.fonts.ready;});
   assert(await page.evaluate(()=>document.fonts.check('600 18px Manrope') && document.fonts.check('italic 400 48px \"Instrument Serif\"')),'Local fonts did not load on '+file);
   assert.equal(await page.locator('.brand img').getAttribute('src'),'assets/mws-owner-logo.png');
   assert.equal(await page.locator('h1').count(),1);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),file+' overflow at '+width);
   assert.equal(await page.locator('.menu').isVisible(),width<=650);
   if(width===1440){
    const links=await page.locator('a[href]').evaluateAll(as=>as.map(a=>a.getAttribute('href')));
    for(const link of links.filter(l=>!l.includes(':')&&!l.startsWith('#'))){
     const url=new URL(link,base); assert.equal((await page.request.get(url.href)).status(),200,link);
    }
   }
  }
 }
 await page.goto(base);
 assert.equal(await page.locator('#catalog-source tr').count(),5);
 assert.equal(await page.locator('[data-preview-rows] tr').count(),3);
 await page.locator('[data-preview-run]').click();
 assert.equal(await page.locator('[data-preview-rows] tr').count(),2);
 assert(await page.locator('[data-preview-run]').isDisabled());
 assert.equal(await page.locator('#catalog-output tr').count(),4);
 assert.equal(await page.locator('#catalog-source tr').count(),5);
 assert(await page.locator('.comparison-disclosure').evaluate(node=>!node.open));
 await page.locator('.comparison-disclosure > summary').click();
 assert((await page.locator('#catalog-status').innerText()).includes('5 source rows → 4 output rows'));
 await page.getByRole('button',{name:'Inspect changes for EF-303'}).click();
 assert((await page.locator('#catalog-inspect').innerText()).includes('It stays blank'));
 const catalog=await Promise.all([page.waitForEvent('download'),page.locator('#catalog-download').click()]);
 await catalog[0].saveAs(path.join(outputDir,'catalog.csv'));
 const catalogCsv=await fs.readFile(path.join(outputDir,'catalog.csv'),'utf8');
 assert.equal(catalogCsv.split('\r\n').length,5);
 assert(catalogCsv.includes('"EF-303","Cotton Throw","","Confirm missing price with source"'));
 const notes=await Promise.all([page.waitForEvent('download'),page.locator('#catalog-notes').click()]);
 await notes[0].saveAs(path.join(outputDir,'notes.txt'));
 assert((await fs.readFile(path.join(outputDir,'notes.txt'),'utf8')).includes('EF-303'));
 await page.locator('#catalog-reset').click();
 assert.equal(await page.locator('#catalog-output tr').count(),0);
 assert(await page.locator('#catalog-empty').isVisible());
 assert.equal(await page.locator('[data-preview-rows] tr').count(),3);
 await page.locator('[data-preview-run]').click();
 await page.locator('[data-preview-reset]').click();
 assert.equal(await page.locator('#catalog-output tr').count(),0);
 assert.equal(await page.locator('.problem-row').count(),3);
 assert.equal(await page.locator('[data-service-price]').count(),5);
 const faq=page.getByRole('button',{name:'I know what’s annoying me, but not what I need. Is that enough?'});
 await faq.click();assert(await page.locator('#faq-answer-1').isVisible());
 await page.keyboard.press('Space');assert(await page.locator('#faq-answer-1').isHidden());
 await page.keyboard.press('Enter');assert(await page.locator('#faq-answer-1').isVisible());
 assert.equal(await faq.evaluate(el=>getComputedStyle(el).caretColor),'rgba(0, 0, 0, 0)');
 await page.locator('.menu').click();assert(await page.locator('#nav').isVisible());await page.keyboard.press('Escape');assert(await page.locator('#nav').isHidden());
 await page.goto(base+'services.html');assert.deepEqual(await page.locator('.price strong').allTextContents(),['$69','$149','$229','$189','$299']);assert.equal(await page.locator('.service-detail').count(),5);assert((await page.locator('.service-detail').first().innerText()).includes('5,000'));await page.locator('.service-detail').first().locator('details summary').first().click();assert((await page.locator('.service-detail').first().innerText()).includes('Remove duplicate'));
 await page.route('**/site-config.js',async route=>{const response=await route.fetch();await route.fulfill({response,body:(await response.text()).replace('"enabled": true','"enabled": false')});});
 await page.reload();assert.deepEqual(await page.locator('.price strong').allTextContents(),['$99','$199','$299','$249','$399']);assert.equal(await page.locator('.price del').count(),0);await page.goto(base);assert(await page.locator('[data-offer]').isHidden());await page.unroute('**/site-config.js');await page.route('**/*',route=>route.continue());
 await page.goto(base+'examples.html');await page.locator('#clean-data').click();assert.equal(await page.locator('#cleanup-rows tr').count(),6);assert.equal(await page.locator('#cleanup-source-rows tr').count(),8);assert((await page.locator('#cleanup-status').innerText()).includes('2 exact duplicates'));
 await page.locator('#fix-format').uncheck();await page.locator('#clean-data').click();assert.equal(await page.locator('#cleanup-rows tr').count(),7);await page.locator('#fix-duplicates').uncheck();await page.locator('#clean-data').click();assert.equal(await page.locator('#cleanup-rows tr').count(),8);
 await page.locator('#reset-data').click();await page.locator('#clean-data').click();const download=await Promise.all([page.waitForEvent('download'),page.locator('#download-cleanup').click()]);await download[0].saveAs(path.join(outputDir,'download-customers.csv'));const csv=await fs.readFile(path.join(outputDir,'download-customers.csv'),'utf8');assert.equal(csv.split('\r\n').length,7);assert(csv.includes('jamie@example.test'));assert(csv.includes('Missing email'));
 await page.getByRole('tab',{name:'Inventory review'}).click();await page.locator('#inventory-check').click();assert.equal(await page.locator('.review-card').count(),3);await page.locator('.review-card select').first().selectOption('reviewed');assert((await page.locator('#inventory-result').innerText()).includes('2 still awaiting'));
 await page.getByRole('tab',{name:'Workflow automation'}).click();await page.locator('#run-workflow').click();assert.equal(await page.locator('#workflow-rows tr').count(),4);assert.equal(await page.locator('#pipeline li.done').count(),4);assert((await page.locator('#workflow-stats').innerText()).includes('$806'));const report=await Promise.all([page.waitForEvent('download'),page.locator('#download-report').click()]);await report[0].saveAs(path.join(outputDir,'download-report.csv'));assert((await fs.readFile(path.join(outputDir,'download-report.csv'),'utf8')).includes('"Towels","15","270"'));await page.locator('#reset-workflow').click();assert(await page.locator('#workflow-result').isHidden());assert.equal(await page.locator('#pipeline li.done').count(),0);
 await page.getByRole('tab',{name:'Sales reporting'}).click();assert.equal(await page.locator('#sales-total').innerText(),'$1,942');assert.equal(await page.locator('#sales-top').innerText(),'Mugs');await page.locator('#month-filter').selectOption('October');await page.locator('#sales-filter').selectOption('Home');assert.equal(await page.locator('#sales-total').innerText(),'$470');assert.equal(await page.locator('#sales-units').innerText(),'20');assert.equal(await page.locator('#sales-rows tr').count(),2);
 await page.getByRole('tab',{name:'Product matching'}).click();await page.locator('#match-products').click();assert((await page.locator('#match-result').innerText()).startsWith('Potential match'));await page.locator('#match-example').selectOption('size');await page.locator('#match-products').click();assert((await page.locator('#match-result').innerText()).startsWith('Do not merge'));await page.locator('#match-example').selectOption('missing');await page.locator('#match-products').click();assert((await page.locator('#match-result').innerText()).startsWith('Not enough information'));
 await page.getByRole('tab',{name:'Product matching'}).focus();await page.keyboard.press('Home');assert.equal(await page.getByRole('tab',{name:'Spreadsheet cleanup'}).getAttribute('aria-selected'),'true');await page.keyboard.press('ArrowRight');assert.equal(await page.getByRole('tab',{name:'Inventory review'}).getAttribute('aria-selected'),'true');
 await page.goto(base+'examples.html#reporting');assert(await page.locator('#panel-reporting').isVisible());
 await page.goto(base+'contact.html?service=reporting');await page.locator('.guided-quote > summary').click();assert.equal(await page.locator('[name=service]').inputValue(),'Reports & Dashboards');await page.locator('button[type=submit]').click();assert(await page.locator('#email-result').isHidden());await page.locator('[name=name]').fill('<img src=x onerror=alert(1)>');await page.locator('[name=email]').fill('test@example.test');await page.locator('textarea[name=description]').fill('Please help with a monthly report.');await page.locator('button[type=submit]').click();assert(await page.locator('#email-result').isVisible());assert((await page.locator('#open-email').getAttribute('href')).startsWith('mailto:'));assert.equal(await page.locator('img[src=x]').count(),0);
 for(const file of ['demo-cleaning.html','demo-coffee.html','demo-landscaping.html']){await page.goto(base+file);await page.waitForURL('**/examples.html');}
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto(base);await page.screenshot({path:path.join(outputDir,`home-${width}.png`),fullPage:true});
  await page.goto(base+'examples.html#reporting');await page.screenshot({path:path.join(outputDir,`lab-${width}.png`),fullPage:true});
  await page.goto(base+'services.html');await page.screenshot({path:path.join(outputDir,`services-${width}.png`),fullPage:true});
 }
 const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});const basic=await nojs.newPage();await basic.goto(base);assert(await basic.locator('#nav').isVisible());assert(await basic.locator('.hero a[href=\"contact.html\"]').isVisible());assert(await basic.locator('#faq-answer-1').isVisible());await basic.goto(base+'contact.html');await basic.locator('.guided-quote > summary').click();assert(await basic.locator('button[type=submit]').isDisabled());assert(await basic.locator('noscript a[href^=mailto]').isVisible());await nojs.close();
 await page.setViewportSize({width:1440,height:1000});await page.emulateMedia({reducedMotion:'reduce'});await page.goto(base);await page.locator('[data-preview-run]').click();assert.equal(await page.evaluate(()=>document.getAnimations().length),0);await page.evaluate(()=>document.body.style.zoom='2');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'200% zoom overflow');assert.deepEqual(errors,[]);await browser.close();console.log(`PASS: ${requests} page/viewport checks, internal links, promotion/pricing, service scopes, side-by-side catalog, decision notes and both downloads, synchronized hero preview, locally loaded fonts and owner logo, three problem paths, FAQ keyboard behavior, five lab demos, alternate cleanup rules, CSV downloads, review decisions, calculated report totals, matching counterexamples, tab keyboard navigation, mobile menu, safe quote preparation, legacy redirects, and no-JS navigation. No browser errors. Artifacts: ${outputDir}`);
})().catch(e=>{console.error(e);process.exit(1)});
