import {purchaseHref} from './ui/cover-lock.js?v=20261025-search-gate';
import {fetchPreviewJson} from './ui/preview-access.js';
import {backLinkMarkup} from './ui/components.js';
import {iconMarkup} from './ui/icons.js';
import {getLanguage,translate} from './ui/language.js';
import {safeLearningHref,restoreDirectoryScroll} from './ui/favorites-navigation.js?v=20261025-refresh-scroll-v2';
import {filterWords} from './word-search.js';
const base='/learning/';
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let indexRequest,version=0,observer;
// Start alongside the directory request, rather than after its first render.
export function preloadWordIndex(){
 indexRequest??=fetchPreviewJson(base+'content/word-index.json').catch(error=>{indexRequest=null;throw error});
 return indexRequest;
}
if(location.hash==='#all-words')preloadWordIndex().catch(()=>{});
// Warm the same request when a user intends to open search; never persist entitlements.
for(const type of ['pointerover','focusin','pointerdown'])document.addEventListener(type,event=>{
 if(event.target.closest?.('a[href*="#all-words"]'))preloadWordIndex().catch(()=>{});
},{passive:true});

const text=(zh,en)=>getLanguage()==='en'?en:zh;
export function wordSearchEntry(){const to=new URL(base,location.origin);to.searchParams.set('returnTo',base+'#words');if(new URLSearchParams(location.search).get('trial')==='1')to.searchParams.set('trial','1');to.hash='all-words';const label=text('搜索全部单词卡','Search all word cards');return `<a class="word-search-nav-link" href="${esc(to.pathname+to.search+to.hash)}" aria-label="${label}" title="${label}">${iconMarkup('search')}</a>`}

export async function renderWordBrowser(app){
 const run=++version;observer?.disconnect();app.dataset.wordBrowserLoading='true';
 // Keep a restored list visible and inert while the fresh protected index loads.
 if(app.dataset.directorySnapshot==='restored'){try{await preloadWordIndex()}catch{}if(run!==version||location.hash!=='#all-words')return;}
const url=new URL(location.href),back=safeLearningHref(url.searchParams.get('returnTo'),base+'#words');
 let query=url.searchParams.get('q')||'',category=url.searchParams.get('category')||'',limit=48,words=[],loading=true;
 const title=text('全部单词','All words');document.title=title+text(' · 很好学',' · Henhaoxue');app.setAttribute('aria-label',title);
 app.innerHTML=`<header class="list-header">${backLinkMarkup(esc(back),text('返回','Back'))}<h1 class="list-page-title">${title}</h1></header><section class="word-browser"><div class="word-browser-controls"><form class="word-search-form" role="search"><div class="ui-search-field word-search-field">${iconMarkup('search')}<input id="word-query" type="search" inputmode="search" enterkeyhint="search" autocomplete="off" maxlength="100" aria-label="${text('搜索中文或英文单词','Search Chinese or English words')}" placeholder="${text('输入中文或英文单词','Search in English or Chinese')}" value="${esc(query)}"><button class="ui-search-clear word-search-clear" type="button" aria-label="${text('清空搜索','Clear search')}"${query?'':' hidden'}>${iconMarkup('close')}</button></div></form><nav class="ui-filter-group word-browser-filters" aria-label="${text('单词分类','Word categories')}"><div class="word-filter-skeleton" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span></div></nav></div><p class="word-result-count" role="status" aria-live="polite" hidden></p><div class="word-browser-results" aria-busy="true"><div class="word-result-grid word-skeleton-grid" aria-hidden="true"><div class="word-skeleton-card"><div class="word-skeleton-image"></div><div class="word-skeleton-copy"><span></span><span></span></div></div><div class="word-skeleton-card"><div class="word-skeleton-image"></div><div class="word-skeleton-copy"><span></span><span></span></div></div><div class="word-skeleton-card"><div class="word-skeleton-image"></div><div class="word-skeleton-copy"><span></span><span></span></div></div><div class="word-skeleton-card"><div class="word-skeleton-image"></div><div class="word-skeleton-copy"><span></span><span></span></div></div><div class="word-skeleton-card"><div class="word-skeleton-image"></div><div class="word-skeleton-copy"><span></span><span></span></div></div><div class="word-skeleton-card"><div class="word-skeleton-image"></div><div class="word-skeleton-copy"><span></span><span></span></div></div></div></div><button class="word-load-more" type="button" hidden>${text('继续查看','Show more')}</button></section>`;
 const input=app.querySelector('#word-query'),clear=app.querySelector('.word-search-clear'),filters=app.querySelector('.word-browser-filters'),results=app.querySelector('.word-browser-results'),count=app.querySelector('.word-result-count'),more=app.querySelector('.word-load-more');
 const key=()=> 'hhx-word-browser:'+query+'|'+category;
 const save=()=>{try{sessionStorage.setItem(key(),JSON.stringify({limit}))}catch{}};
 const syncUrl=()=>{url.searchParams.delete('q');url.searchParams.delete('category');if(query)url.searchParams.set('q',query);if(category)url.searchParams.set('category',category);history.replaceState({...history.state,hhxPath:url.pathname+url.search+url.hash,hhxScroll:0},'',url)};
 const imageUrl=word=>{try{const u=new URL(word.thumbnail,location.origin+base+'reader/');return u.origin===location.origin&&u.pathname.startsWith(base+'thumbs/')?u.pathname:''}catch{return ''}};
 let eagerIds=new Set();
 const card=word=>{const href=new URL(base+'reader/',location.origin);href.searchParams.set('topic','words');href.searchParams.set('id',word.id);href.searchParams.set('back',url.pathname+url.search+url.hash);if(url.searchParams.get('trial')==='1')href.searchParams.set('trial','1');return `<a class="word-result-card" aria-label="${esc(word.word+' · '+word.meaning+(word.locked?text('，需开通',', locked'):''))}" href="${esc(word.locked?purchaseHref:href.pathname+href.search)}"${word.locked?' data-unlock="true"':''}><div class="word-result-image"><img src="${esc(imageUrl(word))}" alt="" width="240" height="192" loading="${eagerIds.has(word.id)?'eager':'lazy'}" decoding="async">${word.locked?`<span class="word-result-lock" aria-label="${text('需开通','Locked')}">${iconMarkup('lock')}</span>`:''}</div><div class="word-result-copy"><h3>${esc(word.word)}</h3><p>${esc(word.meaning)}</p></div></a>`};
 const draw=()=>{
  const matches=filterWords(words,query,category),shown=matches.slice(0,limit);clear.hidden=!input.value;count.hidden=!query.trim();count.textContent=(query.trim()?text('找到','Found'):text('全部','All'))+' · '+matches.length;
  filters.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.category===category)));
  if(!matches.length){results.innerHTML=`<div class="word-search-empty">${iconMarkup('search')}<h2>${text('还没找到这个单词','No words found')}</h2><p>${text('试试中文，或换个英文拼写。','Try Chinese or a different spelling.')}</p><button type="button" class="word-reset">${text('查看全部单词','View all words')}</button></div>`;more.hidden=true;return}
  eagerIds=new Set(shown.slice(0,4).map(word=>word.id));
  const groups=new Map();for(const word of shown){if(!groups.has(word.category))groups.set(word.category,[]);groups.get(word.category).push(word)}
  results.innerHTML=[...groups].map(([name,items])=>`<section class="word-result-group"><h2>${esc(getLanguage()==='en'?translate(name):name)}</h2><div class="word-result-grid">${items.map(card).join('')}</div></section>`).join('');more.hidden=shown.length>=matches.length;
 };
 const reset=()=>{query='';category='';limit=48;input.value='';syncUrl();draw();input.focus({preventScroll:true})};
 app.querySelector('form').addEventListener('submit',event=>{event.preventDefault();input.blur()});
 const change=()=>{query=input.value.slice(0,100);limit=48;syncUrl();if(!loading)draw()};
 input.addEventListener('input',event=>{clear.hidden=!input.value;if(!event.isComposing)change()});input.addEventListener('compositionend',change);
 clear.addEventListener('click',()=>{input.value='';change();input.focus({preventScroll:true})});
 filters.addEventListener('click',event=>{const b=event.target.closest('button[data-category]');if(!b)return;category=b.dataset.category;limit=48;syncUrl();draw()});
 results.addEventListener('click',event=>{if(event.target.closest('.word-reset'))reset();else if(event.target.closest('a'))save()});
 more.addEventListener('click',()=>{limit+=48;draw();save()});
 try{
  const payload=await preloadWordIndex();
  if(run!==version||location.hash!=='#all-words'||!input.isConnected)return;
  loading=false;results.setAttribute('aria-busy','false');words=payload.words;const categories=[...new Set(words.map(w=>w.category))];if(category&&!categories.includes(category))category='';
  filters.innerHTML=[['',text('全部','All')],...categories.map(name=>[name,getLanguage()==='en'?translate(name):name])].map(([value,label])=>`<button class="ui-tag ui-tag--filter" type="button" data-category="${esc(value)}" aria-pressed="${value===category}">${esc(label)}</button>`).join('');
  let saved;try{saved=JSON.parse(sessionStorage.getItem(key())||'null');limit=Math.max(48,Math.min(words.length,saved?.limit||48))}catch{}
  draw();app.dataset.wordBrowserLoading='false';window.dispatchEvent(new Event('hhx-directory-rendered'));observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)&&!more.hidden&&input.isConnected&&location.hash==='#all-words'){limit+=48;draw()}},{rootMargin:'300px'});observer.observe(more);requestAnimationFrame(()=>{if(!input.isConnected)return;restoreDirectoryScroll()});
 }catch{if(!input.isConnected)return;loading=false;results.setAttribute('aria-busy','false');filters.innerHTML='';count.hidden=false;count.textContent=text('单词暂时未能加载','Could not load words');results.innerHTML=`<div class="word-search-empty"><p>${text('请检查网络后重试。','Check your connection and try again.')}</p><button type="button" class="word-reset">${text('重新加载','Retry')}</button></div>`;results.querySelector('button').onclick=()=>renderWordBrowser(app);app.dataset.wordBrowserLoading='false';window.dispatchEvent(new Event('hhx-directory-rendered'))}
}
