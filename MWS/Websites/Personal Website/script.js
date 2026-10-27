const menu = document.querySelector('.menu');
const nav = document.querySelector('#nav');
menu.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  menu.setAttribute('aria-expanded', String(open));
});
nav.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
  nav.classList.remove('open');
  menu.setAttribute('aria-expanded', 'false');
}));
document.querySelector('#year').textContent = new Date().getFullYear();

const pkg = document.querySelector('#package');
const total = document.querySelector('#total');
function updatePrice() {
  const business = pkg.value === '349';
  const monthly = business ? 30 : 20;
  const annual = business ? 300 : 200;
  const setup = Number(pkg.value);
  total.textContent = '$' + setup;
  document.querySelector('#first-care').textContent = '$' + monthly;
  document.querySelector('#launch-total').textContent = '$' + (setup + monthly);
  document.querySelector('#ongoing-care-price').textContent = '$' + monthly + '/month after launch';
  document.querySelector('#annual-care').textContent = 'Or $' + annual + '/year. Hosting, maintenance, and minor edits included. Subscription required while we host your site.';
}
pkg.addEventListener('change', updatePrice);
updatePrice();

const preview=document.querySelector('#preview-site');document.querySelectorAll('.preview-btn').forEach(btn=>btn.addEventListener('click',()=>{const mobile=btn.dataset.device==='mobile';preview.classList.toggle('mobile',mobile);document.querySelectorAll('.preview-btn').forEach(b=>{const selected=b===btn;b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',String(selected));});}));const sections=[...document.querySelectorAll('main section[id]')];const links=[...nav.querySelectorAll('a[href^="#"]')];if('IntersectionObserver'in window){const observer=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting)entry.target.classList.add('visible');});},{threshold:.08});document.querySelectorAll('.reveal').forEach(el=>observer.observe(el));const navObserver=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting){links.forEach(a=>a.classList.toggle('active',a.hash==='#'+entry.target.id));}});},{rootMargin:'-25% 0px -60% 0px'});sections.forEach(s=>navObserver.observe(s));}else document.querySelectorAll('.reveal').forEach(el=>el.classList.add('visible'));const copy=document.querySelector('#copy-email');const toast=document.querySelector('#toast');let toastTimer;copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText('maierwebsolutions@gmail.com');toast.textContent='Email address copied';}catch{toast.textContent='Email: maierwebsolutions@gmail.com';}toast.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.classList.remove('show'),2400);});
// Price estimator creates a ready-to-send inquiry without requiring a server.
const inquiry=document.querySelector('#estimate-inquiry');
function updateInquiry(){
 const business=pkg.value==='349';
 const selected=business?'Business (from $349)':pkg.value==='100'?'Starter introductory ($100)':'Starter regular ($130)';
 const monthly=business?30:20;
 const subject='Website inquiry - '+selected;
 const body='Hello Maier Web Solutions,\n\nI am interested in the '+selected+' website package.\nRequired first month of managed care: $'+monthly+' due at launch. Total through launch: $'+(Number(pkg.value)+monthly)+'. Required ongoing subscription: $'+monthly+'/month or $'+(business?300:200)+'/year until canceled.\nHosting, routine upkeep, and reasonable minor edits (Starter up to 1 hour/month; Business up to 2 hours/month) are included. Larger projects are separately quoted at fixed prices.\n\nMy business: \nWhat I need: \n\nThank you!';
 inquiry.href='mailto:maierwebsolutions@gmail.com?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(body);
}
pkg.addEventListener('change',updateInquiry);

updateInquiry();
// Thin reading progress indicator, throttled to animation frames.
const progress=document.querySelector('#reading-progress');
let progressScheduled=false;
function renderProgress(){
  const scrollable=document.documentElement.scrollHeight-window.innerHeight;
  progress.style.width=(scrollable>0?Math.min(100,Math.max(0,window.scrollY/scrollable*100)):0)+'%';
  progressScheduled=false;
}
function scheduleProgress(){if(!progressScheduled){progressScheduled=true;requestAnimationFrame(renderProgress);}}
window.addEventListener('scroll',scheduleProgress,{passive:true});
window.addEventListener('resize',scheduleProgress,{passive:true});
renderProgress();

// Functional sample-site studio. All examples are fictional and use no external services.
(() => {
const examples={
 landscaping:{brand:'EVERGREEN & CO.',eyebrow:'LANDSCAPING & OUTDOOR CARE',title:'Outdoor spaces,<br>reimagined.',description:'Thoughtful landscaping for the places you call home.',cta:'Get an estimate →',services:['Landscape Design','Lawn Care','Seasonal Cleanup'],serviceTitle:'Beautiful spaces,<br>made simple.',serviceDescription:'From garden planning to seasonal upkeep, we care for every detail.',contactTitle:'Ready for a<br>fresh start?',contactDescription:'Tell us about your outdoor project. We would love to hear your ideas.'},
 cleaning:{brand:'FRESH & FOUND',eyebrow:'HOME & OFFICE CLEANING',title:'A fresher space.<br>A brighter day.',description:'Reliable cleaning for the places that matter most.',cta:'Request a cleaning →',services:['Home Cleaning','Office Cleaning','Deep Cleans'],serviceTitle:'Clean spaces.<br>Clear minds.',serviceDescription:'Flexible cleaning options tailored to your home or workspace.',contactTitle:'Let’s make<br>it spotless.',contactDescription:'Reach out for a customized cleaning plan.'},
 coffee:{brand:'DAYBREAK COFFEE',eyebrow:'NEIGHBORHOOD COFFEE HOUSE',title:'Good mornings<br>start here.',description:'Fresh coffee, warm pastries, and room to stay awhile.',cta:'Explore the menu →',services:['Espresso Bar','Fresh Pastries','Seasonal Drinks'],serviceTitle:'Made with care.<br>Served with joy.',serviceDescription:'Find your new favorite drink and a little moment of calm.',contactTitle:'Come say<br>hello.',contactDescription:'Stop by for coffee and a friendly welcome.'}
};
const select=document.querySelector('#demo-industry');
const brand=document.querySelector('#demo-brand');
const eyebrow=document.querySelector('#demo-eyebrow');
const title=document.querySelector('#demo-title');
const description=document.querySelector('#demo-description');
const cta=document.querySelector('#demo-cta');
const bottom=document.querySelector('.preview-bottom');
const site=document.querySelector('#preview-site');
const buttons=[...document.querySelectorAll('.demo-nav')];
let panel='home';
function render(){
 const data=examples[select.value];
 site.dataset.industry=select.value;
 brand.textContent=data.brand;
 document.querySelector('#demo-concept-label').textContent=data.brand+' — CONCEPT';
 bottom.replaceChildren(...data.services.map(name=>{const el=document.createElement('div');el.textContent=name;return el;}));
 if(panel==='home'){eyebrow.textContent=data.eyebrow;title.innerHTML=data.title;description.textContent=data.description;cta.textContent=data.cta;}
 else if(panel==='services'){eyebrow.textContent='WHAT WE OFFER';title.innerHTML=data.serviceTitle;description.textContent=data.serviceDescription;cta.textContent='Get in touch →';}
 else {eyebrow.textContent='LET’S CONNECT';title.innerHTML=data.contactTitle;description.textContent=data.contactDescription;cta.textContent='Back to home →';}
 buttons.forEach(b=>{const active=b.dataset.panel===panel;b.classList.toggle('selected',active);b.setAttribute('aria-pressed',String(active));});
}
select.addEventListener('change',()=>{panel='home';render();});
buttons.forEach(b=>b.addEventListener('click',()=>{panel=b.dataset.panel;render();}));
cta.addEventListener('click',()=>{panel=panel==='contact'?'home':panel==='home'&&select.value==='coffee'?'services':'contact';render();});
render();
})();
