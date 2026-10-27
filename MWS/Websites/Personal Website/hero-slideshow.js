(()=>{
 const root=document.getElementById('showcase'); if(!root)return;
 const slides=[
  {name:'Evergreen & Co.',url:'demo-landscaping.html',address:'evergreen-co.demo',title:'Evergreen and Co. landscaping website preview'},
  {name:'Fresh & Found',url:'demo-cleaning.html',address:'fresh-and-found.demo',title:'Fresh and Found cleaning website preview'},
  {name:'Daybreak Coffee',url:'demo-coffee.html',address:'daybreak-coffee.demo',title:'Daybreak Coffee website preview'}
 ];
 const frame=root.querySelector('#hero-slide-frame'),link=root.querySelector('#hero-slide-link'),address=root.querySelector('.browserbar span:nth-child(2)'),dots=[...root.querySelectorAll('[data-slide]')];
 const viewport=root.querySelector('.hero-slide-window');
 function fitFrame(){if(viewport){viewport.style.setProperty('--hero-frame-scale',String(viewport.clientWidth/1200));}}
 if('ResizeObserver' in window){new ResizeObserver(fitFrame).observe(viewport)}else{window.addEventListener('resize',fitFrame)}
 fitFrame();
 let index=0,timer=null,paused=false;
 const reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
 function render(next){index=(next+slides.length)%slides.length;const s=slides[index];frame.classList.add('fading');frame.src=s.url;frame.title=s.title;address.textContent=s.address;link.href=s.url;link.setAttribute('aria-label','Open '+s.name+' website demo');link.textContent='Explore '+s.name+' demo ↗';dots.forEach((b,i)=>b.setAttribute('aria-pressed',String(i===index)));}
 frame.addEventListener('load',()=>frame.classList.remove('fading'));
 function stop(){if(timer){clearInterval(timer);timer=null}}
 function start(){stop();if(!reduce&&!paused&&!document.hidden)timer=setInterval(()=>render(index+1),5000)}
 function select(n){render(n);start()}
 root.querySelector('#hero-slide-prev').addEventListener('click',()=>select(index-1));root.querySelector('#hero-slide-next').addEventListener('click',()=>select(index+1));
 dots.forEach(b=>b.addEventListener('click',()=>select(Number(b.dataset.slide))));
 root.addEventListener('mouseenter',()=>{paused=true;stop()});root.addEventListener('mouseleave',()=>{paused=false;start()});
 root.addEventListener('focusin',()=>{paused=true;stop()});root.addEventListener('focusout',e=>{if(!root.contains(e.relatedTarget)){paused=false;start()}});
 document.addEventListener('visibilitychange',()=>document.hidden?stop():start());
 render(0);start();
})();
