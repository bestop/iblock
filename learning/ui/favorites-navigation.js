import {readCollection} from './content-types.js';
// QA navigation: explicit source routes, native back when available, safe fallbacks.
export const learningBase='/learning/';
const pendingKey='hhx-live-navigation-pending';
const directoryScrollKey='hhx-live-directory-scroll';
function rememberDirectoryScroll(){if(location.pathname!==learningBase)return;try{const positions=JSON.parse(sessionStorage.getItem(directoryScrollKey)||'{}');positions[route()]=Math.max(0,scrollY);sessionStorage.setItem(directoryScrollKey,JSON.stringify(Object.fromEntries(Object.entries(positions).slice(-24))))}catch{}}
const route=()=>location.pathname+location.search+location.hash;
let scrollRestoreVersion=0;
export function safeLearningHref(value,fallback=learningBase+'#home'){
 if(!value||String(value).length>12000)return fallback;
 try{const u=new URL(value,location.origin);if(u.origin!==location.origin||![learningBase,learningBase+'reader/',learningBase+'account/','/'].includes(u.pathname))return fallback;return u.pathname+u.search+u.hash}catch{return fallback}
}
function pageKey(href){const u=new URL(href,location.origin);return u.pathname===learningBase+'reader/'?[u.pathname,u.searchParams.get('topic')||'phrases',u.searchParams.get('id')||u.searchParams.get('category')||'',u.searchParams.get('collection')||'',u.searchParams.get('level')||''].join('|'):u.pathname+u.hash}
function catalogHref(href=route()){const u=new URL(href,location.origin),kind=u.searchParams.get('topic');return learningBase+'#'+(kind==='words'?'words':kind==='readings'?'readings':'scenes')}
function viableReturn(href,fallback){const to=safeLearningHref(href,fallback);if(!to)return fallback;const u=new URL(to,location.origin),collection=u.searchParams.get('collection');if(u.pathname===learningBase+'reader/'&&['words','readings','phrases'].includes(collection)){const saved=readCollection(collection),id=u.searchParams.get('id'),savedId=collection==='words'?id:(collection==='readings'?'reading-':'phrase-')+id;if(!saved.length||(id&&!saved.includes(savedId)))return catalogHref(to);}return to}
export function readerBackHref(fallback){const to=viableReturn(new URLSearchParams(location.search).get('back'),fallback);return to&&pageKey(to)===pageKey(route())?fallback:to}
export function emptyCollectionHref(kind){const u=new URL(learningBase,location.origin);u.searchParams.set('filter',kind);u.searchParams.set('returnTo',learningBase+'#'+(kind==='phrases'?'scenes':kind));u.hash='favorites';return u.pathname+u.search+u.hash}
export function favoritesHref(){if(location.pathname===learningBase&&location.hash==='#favorites')return route();const back=readerBackHref('');if(back&&new URL(back,location.origin).hash==='#favorites')return back;const u=new URL(learningBase,location.origin);u.searchParams.set('returnTo',route());u.hash='favorites';return u.pathname+u.search+u.hash}
export function favoriteReturnHref(){const target=viableReturn(new URLSearchParams(location.search).get('returnTo'),learningBase+'#home');return new URL(target,location.origin).hash==='#favorites'?learningBase+'#home':target}
export function readerHref(href){const u=new URL(safeLearningHref(href),location.origin);u.searchParams.set('back',route());if(location.hash==='#favorites')u.searchParams.set('collection',u.searchParams.get('topic')||'phrases');return u.pathname+u.search+u.hash}
export const favoriteItemHref=readerHref;
export function accountHref(view=''){const u=new URL(learningBase+'account/',location.origin);u.searchParams.set('back',route());u.searchParams.set('view',view||'account');return u.pathname+u.search}
// Authentication exits forced trial mode but retains the original learning context.
export function authenticatedLearningHref(value,depth=0){
 const u=new URL(safeLearningHref(value),location.origin);u.searchParams.delete('trial');
 for(const key of ['back','returnTo'])if(u.searchParams.has(key)){
  const nested=u.searchParams.get(key);
  if(depth<4)u.searchParams.set(key,authenticatedLearningHref(nested,depth+1));else u.searchParams.delete(key);
 }
 return u.pathname+u.search+u.hash;
}
function savePending(href){rememberDirectoryScroll();try{history.replaceState({...history.state,hhxScroll:scrollY},'',location.href);sessionStorage.setItem(pendingKey,JSON.stringify({from:route(),to:href,time:Date.now()}))}catch{}}
function changeDirectoryRoute(to,replace=false){const target=new URL(to,location.origin);if(location.pathname!==learningBase||target.pathname!==learningBase)return false;const previous=route();scrollTo(0,0);history[replace?'replaceState':'pushState']({hhxPath:to,hhxPrevious:replace?null:previous,hhxScroll:0},'',to);try{sessionStorage.removeItem(pendingKey)}catch{}window.dispatchEvent(new Event('hhx-live-route-change'));return true}
export function navigateTo(href){const to=safeLearningHref(href);if(to===route())return;savePending(to);if(!changeDirectoryRoute(to))location.assign(to)}
export function openFavorites(){const to=favoritesHref();if(to===route())return;const back=readerBackHref('');if(back===to)navigateBack(to);else navigateTo(to)}
export function navigateBack(href){let to=viableReturn(href,learningBase+'#home');if(pageKey(to)===pageKey(route()))to=location.pathname===learningBase+'reader/'?catalogHref():learningBase+'#home';if(location.pathname===learningBase+'reader/'&&new URL(to,location.origin).pathname===learningBase){const ref=new URL(document.referrer||location.href),target=new URL(to,location.origin);if(history.state?.hhxPrevious===to&&history.length>1&&ref.origin===target.origin&&ref.pathname===target.pathname&&ref.search===target.search){history.back();return}try{const positions=JSON.parse(sessionStorage.getItem(directoryScrollKey)||'{}');sessionStorage.setItem(pendingKey,JSON.stringify({to,time:Date.now(),returnScroll:positions[to]||0}))}catch{}location.replace(to);return}if(history.state?.hhxPrevious===to&&history.length>1)history.back();else if(!changeDirectoryRoute(to,true))location.replace(to)}
function registerRoute(){const path=route();if(history.state?.hhxPath===path)return;let pending;try{pending=JSON.parse(sessionStorage.getItem(pendingKey)||'null');sessionStorage.removeItem(pendingKey)}catch{}const previous=pending?.to===path&&Date.now()-pending.time<60000?(pending.from||null):null;history.replaceState({...history.state,hhxPath:path,hhxPrevious:previous,hhxScroll:pending?.to===path?Math.max(0,Number(pending.returnScroll)||0):0},'',location.href)}
export function updateReaderLocation(id,difficulty){const u=new URL(location.href);u.searchParams.set('id',id);u.searchParams.delete('category');if(difficulty)u.searchParams.set('difficulty',difficulty);history.replaceState({...history.state,hhxPath:u.pathname+u.search+u.hash},'',u)}
export function restoreDirectoryScroll(){const version=++scrollRestoreVersion,path=route(),top=Math.max(0,Number(history.state?.hhxScroll)||0);const restore=()=>{if(version===scrollRestoreVersion&&route()===path)scrollTo(0,top)};restore();requestAnimationFrame(()=>requestAnimationFrame(restore))}
function installHeaderClickGuard(){
 let pointer=null;
 const header=()=>document.querySelector('.list-header')||document.querySelector('.category-row.ui-study-header')||document.querySelector('.topbar');
 document.addEventListener('pointerdown',event=>{const bar=header();pointer={time:Date.now(),path:location.pathname,fromHeader:!!bar?.contains(event.target)}},true);
 document.addEventListener('click',event=>{
  if(event.defaultPrevented||event.button!==0||event.detail===0)return;
  const bar=header(),link=event.target.closest?.('a[href]');if(!bar||!link||bar.contains(link))return;
  const rect=bar.getBoundingClientRect(),depth=Number.parseFloat(getComputedStyle(bar).height)||64;
  const headerPosition=event.clientY>=0&&event.clientY<Math.max(depth,rect.bottom);
  const headerGesture=pointer&&pointer.path===location.pathname&&pointer.fromHeader&&Date.now()-pointer.time<1600;
  if(!headerPosition&&!headerGesture)return;
  event.preventDefault();event.stopImmediatePropagation();
  try{const key='hhx-live-header-diagnostics',items=JSON.parse(sessionStorage.getItem(key)||'[]');items.push({time:Date.now(),path:location.pathname,view:location.hash,y:event.clientY,headerTop:rect.top,headerBottom:rect.bottom,scroll:scrollY,width:innerWidth,height:innerHeight});sessionStorage.setItem(key,JSON.stringify(items.slice(-16)))}catch{}
 },true);
}

export function installNavigation(){
 if(window.__hhxPreviewNavigation)return;window.__hhxPreviewNavigation=true;try{history.scrollRestoration='manual'}catch{}
 // A reload is a fresh view, not a return from a reader. Reset once at startup;
 // subsequent back/forward navigations must retain their own saved positions.
 if(window.__hhxDirectoryFreshStart||globalThis.performance?.getEntriesByType?.('navigation')[0]?.type==='reload'){
  try{history.replaceState({...history.state,hhxScroll:0},'',location.href);sessionStorage.removeItem(pendingKey)}catch{}
  scrollTo(0,0);
 }
 registerRoute();
 document.addEventListener('click',event=>{const link=event.target.closest?.('a[href]');if(!link||event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||link.target==='_blank'||link.hasAttribute('download'))return;const to=safeLearningHref(link.href,'');if(!to)return;if(link.classList.contains('back-nav-link')){event.preventDefault();navigateBack(to)}else if(to!==route()){if(location.pathname===learningBase&&new URL(to,location.origin).pathname===learningBase){event.preventDefault();navigateTo(to)}else savePending(to)}});
 installHeaderClickGuard();
 window.addEventListener('hashchange',registerRoute);window.addEventListener('popstate',registerRoute);
 window.addEventListener('pagehide',()=>{rememberDirectoryScroll();try{history.replaceState({...history.state,hhxScroll:scrollY},'',location.href)}catch{}});
}
