const DATA_URL='./data/noticias.json';
const REFRESH_MS=60*60*1000;
let news=[];let activeFilter='Todas';
const grid=document.getElementById('newsGrid');
const dialog=document.getElementById('articleDialog');
const articleContent=document.getElementById('articleContent');

async function loadNews(force=false){
  try{
    const url=DATA_URL+(force?'?t='+Date.now():'');
    const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);
    const data=await r.json();news=Array.isArray(data.items)?data.items:[];
    document.getElementById('lastUpdate').textContent=data.updated_at?formatDate(data.updated_at):'Actualizado';
    render();
  }catch(e){if(!news.length)grid.innerHTML='<div class="loading">No se han podido cargar las noticias. Comprueba la conexión.</div>';}
}
function formatDate(v){return new Intl.DateTimeFormat('es-ES',{dateStyle:'short',timeStyle:'short'}).format(new Date(v))}
function relativeDate(v){const d=new Date(v),diff=Math.max(0,Date.now()-d.getTime()),m=Math.floor(diff/60000);if(m<60)return 'Hace '+m+' min';const h=Math.floor(m/60);if(h<24)return 'Hace '+h+' h';return new Intl.DateTimeFormat('es-ES',{day:'numeric',month:'short'}).format(d)}
function render(){
  const filtered=activeFilter==='Todas'?news:news.filter(n=>(n.categories||[]).includes(activeFilter)||n.source_type===activeFilter);
  document.getElementById('sectionTitle').textContent=activeFilter==='Todas'?'Últimas noticias':activeFilter;
  document.getElementById('count').textContent=filtered.length+' noticias';
  grid.innerHTML=filtered.map((n,i)=>card(n,i)).join('')||'<div class="loading">No hay noticias en esta categoría.</div>';
  document.querySelectorAll('.news-card').forEach(c=>c.onclick=()=>openArticle(c.dataset.id));
  document.querySelectorAll('.topic').forEach(t=>t.classList.toggle('active',t.dataset.filter===activeFilter));
  const latest=[...news].sort((a,b)=>new Date(b.published)-new Date(a.published)).slice(0,8);
  const text=latest.map(n=>`<span>• ${escapeHtml(n.title)}</span>`).join('');document.getElementById('tickerTrack').innerHTML=text+text;
  renderPulse();
}
function renderPulse(){
  const labels=['Sentencias','Convenios','Salarios','Canarias','Hostelería'];
  const stats=labels.map(label=>[label,news.filter(n=>(n.categories||[]).includes(label)).length]);
  document.getElementById('pulseStats').innerHTML=stats.map(([l,c])=>`<div class="pulse-stat"><strong>${c}</strong><small>${l}</small></div>`).join('');
}
function card(n,i){
  const isSentence=n.type==='sentencia'||(n.categories||[]).includes('Sentencias');
  const isCanary=(n.categories||[]).includes('Canarias');
  const size=i===0?'featured':i<3?'medium':'compact';
  const cls=`news-card ${size} ${isSentence?'sentence':''} ${isCanary?'canary':''}`;
  const badgeClass=n.source_type==='UGT'?'ugt':isSentence?'sentencia':isCanary?'canarias':'';
  return `<article class="${cls}" data-id="${escapeAttr(n.id)}"><div class="meta"><span class="badge ${badgeClass}">${escapeHtml(n.source_label||'FUENTE')}</span><small>${relativeDate(n.published)}</small></div><h3>${escapeHtml(n.title)}</h3><p>${escapeHtml(n.summary||'')}</p><div class="source">${escapeHtml(n.source)} <span class="read">Leer →</span></div></article>`;
}
function openArticle(id){
  const n=news.find(x=>x.id===id);if(!n)return;
  const isSentence=n.type==='sentencia'||(n.categories||[]).includes('Sentencias');
  articleContent.innerHTML=`<button class="article-close" aria-label="Cerrar">×</button><span class="badge ${n.source_type==='UGT'?'ugt':isSentence?'sentencia':''}">${escapeHtml(n.source_label||'FUENTE')}</span><h2 class="article-title">${escapeHtml(n.title)}</h2><p class="source">${escapeHtml(n.source)} · ${formatDate(n.published)}</p>${section('¿Qué ha pasado?',n.what_happened)}${section('¿A quién afecta?',n.who_affected)}${section('¿Qué significa?',n.impact)}${n.ugt_position?section('Posición UGT',n.ugt_position):''}<div class="article-section"><h4>Fuente original</h4><p>Consulta siempre el documento original.</p><a class="source-link" href="${escapeAttr(n.url)}" target="_blank" rel="noopener noreferrer">Ver fuente original →</a></div>`;
  articleContent.querySelector('.article-close').onclick=()=>dialog.close();dialog.showModal();
}
function section(title,text){return text?`<div class="article-section"><h4>${title}</h4><p>${escapeHtml(text)}</p></div>`:''}
function escapeHtml(s=''){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}
function escapeAttr(s=''){return escapeHtml(s)}
function setFilter(f){activeFilter=f;render();closeDrawer()}
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>setFilter(b.dataset.filter)));
document.getElementById('refreshBtn').onclick=()=>loadNews(true);
const drawer=document.getElementById('drawer'),overlay=document.getElementById('overlay');
function openDrawer(){drawer.classList.add('open');overlay.classList.add('show');drawer.setAttribute('aria-hidden','false')}
function closeDrawer(){drawer.classList.remove('open');overlay.classList.remove('show');drawer.setAttribute('aria-hidden','true')}
document.getElementById('menuBtn').onclick=openDrawer;document.getElementById('closeMenu').onclick=closeDrawer;overlay.onclick=closeDrawer;
const topicNames=['Todas','Derechos laborales','Sentencias','Convenios','Salarios','Empleo','Canarias','Hostelería','UGT'];
document.getElementById('topics').innerHTML=topicNames.map(x=>`<button class="topic" data-filter="${escapeAttr(x)}">${escapeHtml(x)}</button>`).join('');
document.querySelectorAll('.topic').forEach(b=>b.onclick=()=>setFilter(b.dataset.filter));
let deferredPrompt;window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();deferredPrompt=e;const btn=document.getElementById('installBtn');btn.hidden=false;btn.onclick=async()=>{await deferredPrompt.prompt();deferredPrompt=null;btn.hidden=true}});
if('serviceWorker' in navigator)navigator.serviceWorker.register('./sw.js').catch(()=>{});
loadNews();setInterval(()=>loadNews(true),REFRESH_MS);
