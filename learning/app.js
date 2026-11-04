import {learningFavoritesReady} from './ui/learning-favorites.js?v=cloud-v1';
const directoryRequest=fetchPreviewJson('/learning/content/directory.json');
directoryRequest.catch(()=>{});
// Favorite sync is independent of content loading; its own notice provides retry.
learningFavoritesReady.catch(()=>{});
import {renderWordBrowser,wordSearchEntry} from './word-browser.js?v=20261025-return-snapshot';
import {fetchPreviewJson,renderPreviewError,previewAccess} from './ui/preview-access.js';
import './ui/card-feedback.js?v=20261025-word-press';
import './trial-directory.js?v=20261104-unlock-blocks';
import {favoriteReturnHref,favoriteItemHref,readerHref,restoreDirectoryScroll,installNavigation,navigateTo} from './ui/favorites-navigation.js?v=20261025-refresh-scroll-v2';
import {iconMarkup} from './ui/icons.js?v=20261022-context-gloss-v1';
import {getLanguage,translate,translateTree} from './ui/language.js?v=20261023-add-hhx-desktop';
import {tipsMarkup} from './tips.js?v=20261023-global-icons';
import {backLinkMarkup} from './ui/components.js?v=20261021-menu-insets';
import {contentTypes,readCollection,collectionCount,removeCollection} from './ui/content-types.js';
'use strict';
// The word browser owns its index; unrelated topic data must not delay its shell.
installNavigation();
const initialWordBrowser=location.hash==='#all-words';
if(initialWordBrowser)renderWordBrowser(document.getElementById('app'));
const [directoryData]=await Promise.all([directoryRequest,previewAccess]).catch(error=>{renderPreviewError(document.getElementById('app'),error);throw error});
installNavigation();
const root=new URL('./',import.meta.url).pathname;
const paths={arrow:'M5 12h14m-6-6 6 6-6 6',back:'M19 12H5m6-6-6 6 6 6',book:'M12 7c-3-2-7-2-10-1v14c3-1 7-1 10 1m0-14c3-2 7-2 10-1v14c-3-1-7-1-10 1V7',chat:'M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-3 3V11.5A8.5 8.5 0 0 1 9.5 3h3a8.5 8.5 0 0 1 8.5 8.5Z',pin:'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Zm-5 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0',box:'m3 7 9-4 9 4-9 4-9-4Zm0 0v10l9 4 9-4V7M12 11v10',house:'m3 11 9-8 9 8M5 10v11h14V10M9 21v-7h6v7',sun:'M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5',pick:'m3 21 12-12M8 3c6-1 11 4 13 10l-5-4-3-1-1-3-4-2Z',shield:'m12 3 9 4v6c0 5-9 9-9 9s-9-4-9-9V7l9-4Z',team:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8M17 4a4 4 0 0 1 0 8m2 3a4 4 0 0 1 3 4v2',wifi:'M2 8a16 16 0 0 1 20 0M5 12a11 11 0 0 1 14 0M8 16a6 6 0 0 1 8 0M12 20h.01',play:'m9 5 10 7-10 7V5',sound:'m11 5-6 4H2v6h3l6 4V5m4 3a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14'};
const icon=n=>`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[n]||paths.chat}"/></svg>`;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const scenes=directoryData.scenes;
// Complete reviewed 200-phrase set, source: react/data.json.
const phrases=directoryData.phrases;
const phraseImages=directoryData.images;
const app=document.getElementById('app');
const read=k=>{try{return JSON.parse(localStorage.getItem('hhx-learning-'+k))}catch{return null}};
const write=(k,v)=>{try{localStorage.setItem('hhx-learning-'+k,JSON.stringify(v))}catch{}};
const readingSamples=directoryData.readings;
const wordTopics=[{"name":"基础方块世界","count":87,"id":"basic_block_world_things-p01-c01","examples":"认识玩家、物品和游戏里的基本概念。","cover":"category-covers/v1/basics-c617e0e55b-400.webp","coverLarge":"category-covers/v1/basics-de4e2806db-800.webp"},{"name":"方块与建造","count":267,"id":"blocks_and_building-p01-c01","examples":"认识常见方块，学会说出建造用的材料。","cover":"category-covers/v1/building-0dde015469-400.webp","coverLarge":"category-covers/v1/building-e67454109c-800.webp"},{"name":"动物与伙伴","count":102,"id":"animals_and_friends-p01-c01","examples":"认识身边的动物和可以结交的伙伴。","cover":"category-covers/v1/animals-6677b45465-400.webp","coverLarge":"category-covers/v1/animals-6252f94ef1-800.webp"},{"name":"怪物与首领","count":57,"id":"monsters_and_bosses-p01-c01","examples":"认识冒险中会遇见的怪物与首领。","cover":"category-covers/v1/monsters-8c056b9004-400.webp","coverLarge":"category-covers/v1/monsters-b6c72cace7-800.webp"},{"name":"食物与耕作","count":102,"id":"food_and_farming-p01-c01","examples":"认识食物、作物，了解种植和收获。","cover":"category-covers/v1/farming-c922dc2783-400.webp","coverLarge":"category-covers/v1/farming-c9ca1f479c-800.webp"},{"name":"工具与装备","count":147,"id":"tools_and_gear-p01-c01","examples":"认识采集、制作和战斗常用的装备。","cover":"category-covers/v1/tools-418568d629-400.webp","coverLarge":"category-covers/v1/tools-b57559db63-800.webp"},{"name":"地点与生物群系","count":102,"id":"places_and_biomes-p01-c01","examples":"认识不同地形，探索各式各样的环境。","cover":"category-covers/v1/biomes-904e2fea8e-400.webp","coverLarge":"category-covers/v1/biomes-d9d0b05e44-800.webp"},{"name":"建筑与宝藏","count":117,"id":"structures_and_treasures-p01-c01","examples":"认识村庄、遗迹和探索中发现的建筑。","cover":"category-covers/v1/treasures-7bd8d77540-400.webp","coverLarge":"category-covers/v1/treasures-d923f631a6-800.webp"},{"name":"颜色与材料","count":162,"id":"colors_and_materials-p01-c01","examples":"认识颜色、原料和制作物品的材料。","cover":"category-covers/v1/materials-ab44ddf280-400.webp","coverLarge":"category-covers/v1/materials-8d5ffaba06-800.webp"},{"name":"动作词汇","count":102,"id":"action_words-p01-c01","examples":"学会描述挖掘、放置和制作等动作。","cover":"category-covers/v1/actions-55491f0a4d-400.webp","coverLarge":"category-covers/v1/actions-148e35fca6-800.webp"}];
const sceneImages=["basic_block_world_things-p01-c01","basic_block_world_things-p02-c14","basic_block_world_things-p01-c11","basic_block_world_things-p01-c12","basic_block_world_things-p01-c07","basic_block_world_things-p02-c10","basic_block_world_things-p01-c08","monsters_and_bosses-p01-c03","basic_block_world_things-p01-c05","basic_block_world_things-p01-c02"];
let resumeObserver;
function sizeResumeThumbnail(){
 resumeObserver?.disconnect();const frame=app.querySelector('.continue-thumbnail'),copy=app.querySelector('.continue-copy'),image=frame?.querySelector('img');if(!frame||!copy||!image)return;
 const resize=()=>{if(!frame.isConnected)return;const height=Math.max(innerWidth<=700?56:64,Math.ceil(copy.getBoundingClientRect().height));const ratio=image.naturalWidth&&image.naturalHeight?image.naturalWidth/image.naturalHeight:5/4;frame.style.height=height+'px';frame.style.width=height*ratio+'px'};
 resize();image.addEventListener('load',resize,{once:true});resumeObserver=new ResizeObserver(resize);resumeObserver.observe(copy);
}
function home(){document.title='学习主页 · 很好学';const activity=read('last-activity');let resume=null;if(activity?.kind==='readings'){const item=readingSamples.find(r=>'reading-'+r.id===activity.id);if(item)resume={href:root+'reader/?topic=readings&id='+item.id+(activity.level?'&level='+encodeURIComponent(activity.level):''),image:root+(item.imageThumb||item.imageSrc),label:translate('游戏小百科')+' · '+(getLanguage()==='en'?item.word:item.meaning)}}else if(activity?.kind==='words'&&typeof activity.id==='string'){resume={href:root+'reader/?topic=words&id='+encodeURIComponent(activity.id),image:root+'thumbs/'+encodeURIComponent(activity.id)+'.webp',kind:'words',label:translate('看图学单词')+(activity.title?' · '+activity.title:'')}}else{const p=phrases.find(p=>'phrase-'+p[1]===activity?.id||(!activity&&p[1]===read('last')));if(p)resume={href:root+'reader/?id='+p[1],image:root+phraseImages[p[1]].src.replace(/^\.\.\//,''),label:translate(scenes[p[0]][0])+' · '+(getLanguage()==='en'?'Phrase '+(phrases.filter(q=>q[0]===p[0]).indexOf(p)+1):'第 '+(phrases.filter(q=>q[0]===p[0]).indexOf(p)+1)+' 句')}}app.innerHTML=`<section class="intro"><h1>今天想学什么？</h1><p>从喜欢的世界出发，认识单词，学会和队友用英语交流。</p></section>${resume?`<a class="continue" href="${esc(resume.href)}"><span class="continue-thumbnail${resume.kind==='words'?' is-word':''}"><img src="${esc(resume.image)}" alt="" width="80" height="64"></span><div class="continue-copy"><strong>继续上次学习</strong><p>${esc(resume.label)}</p></div><span class="continue-arrow">${icon('arrow')}</span></a>`:''}<div class="topics"><a class="topic" href="#words" aria-label="看图学单词，1245 张单词卡，10 大主题"><div class="art cover"><img src="./cover-vocabulary-v4.webp" alt="树、羊和箱子带有 tree、sheep、chest 英文标注的方块世界" width="1200" height="675" fetchpriority="high"></div><div class="topic-body"><h2>看图学单词</h2><p class="topic-description">看图认识熟悉的方块与角色，听单词发音和例句。</p><div class="topic-tags"><span>1245 张单词卡</span><span>10 大主题</span></div></div></a><a class="topic" href="#scenes" aria-label="游戏常用对话，200 句常用语，10 个场景"><div class="art cover"><img src="./cover-speaking-v4.webp" alt="两位方块世界伙伴互相挥手打招呼" width="1200" height="675" fetchpriority="high"></div><div class="topic-body"><h2>游戏常用对话</h2><p class="topic-description">跟着游戏场景学英语，找队友、借物资，一起合作冒险。</p><div class="topic-tags"><span>200 句常用语</span><span>10 个场景</span></div></div></a><a class="topic" href="#readings" aria-label="游戏小百科，${readingSamples.length} 篇小知识，10 个主题"><div class="art cover"><img src="./cover-readings-v1.webp" alt="通过简单英语了解方块世界里的物品和生物" width="1200" height="675"></div><div class="topic-body"><h2>游戏小百科</h2><p class="topic-description">发现游戏小知识，学会实用小技巧，也读懂其中的英语。</p><div class="topic-tags"><span>${readingSamples.length} 篇小知识</span><span>10 个主题 · 三档难度</span></div></div></a></div>`;}
function phrasePage(id){location.replace(root+'reader/?id='+encodeURIComponent(id)+'&back='+encodeURIComponent(root+'#scenes'));}
const listBack=(title='',back=root+'#home')=>`<header class="list-header">${backLinkMarkup(esc(back))}<h1 class="list-page-title">${title}</h1></header>`;
function wordsPage(){document.title='看图学单词 · 很好学';app.innerHTML=listBack('看图学单词').replace('</header>',wordSearchEntry()+'</header>')+`<div class="topic-list-grid">${wordTopics.map(t=>`<a class="list-card" data-cover-tone="${t.name==='怪物与首领'?'dark':'light'}" href="${root}reader/?topic=words&category=${encodeURIComponent(t.name)}"><div class="list-art"><img src="${root}${t.cover}" srcset="${root}${t.cover} 400w, ${root}${t.coverLarge} 800w" sizes="(max-width:700px) calc((100vw - 52px)/2), (max-width:1000px) calc((100vw - 64px)/2), 360px" alt="${t.name}" width="800" height="640"><span class="list-badges"><span class="ui-tag">${t.count} 张单词卡</span></span></div><div class="list-copy"><h2>${t.name}</h2><p>${t.examples}</p></div></a>`).join('')}</div>`;}
function scenePage(){document.title='游戏常用对话 · 很好学';app.innerHTML=listBack('游戏常用对话')+`<div class="topic-list-grid">${scenes.map((s,i)=>{const first=phrases.find(p=>p[0]===i);return `<a class="list-card" href="${root}reader/?id=${first[1]}"><div class="list-art"><img src="${root}scene-covers/${["greetings","meetup","directions","supplies","building","survival","exploring","rescue","teamwork","connection"][i]}.webp" alt="${s[0]}" width="1200" height="675"><span class="list-badges"><span class="ui-tag">${s[1]} ${getLanguage()==='en'?'phrases':'句常用语'}</span></span></div><div class="list-copy"><h2>${s[0]}</h2><p>${s[3]}</p></div></a>`}).join('')}</div>`;}
let readingLevel=new URLSearchParams(location.search).get('level')||'全部';if(!['全部','入门','进阶','挑战'].includes(readingLevel))readingLevel='全部';
function readingsPage(){readingLevel=new URLSearchParams(location.search).get('level')||'全部';if(!['全部','入门','进阶','挑战'].includes(readingLevel))readingLevel='全部';document.title='游戏小百科 · 很好学';app.innerHTML=listBack('游戏小百科')+`<nav class="favorite-filters ui-filter-group reading-level-filters" aria-label="阅读难度">${['全部','入门','进阶','挑战'].map(level=>`<button class="ui-tag ui-tag--filter" type="button" data-reading-level="${level}" aria-pressed="${readingLevel===level}">${level}</button>`).join('')}</nav><div class="topic-list-grid readings-grid">${readingSamples.map(r=>`<a class="list-card" data-reading-card-level="${r.level}"${readingLevel!=='全部'&&r.level!==readingLevel?' hidden':''} href="${root}reader/?topic=readings&id=${r.id}"><div class="list-art"><img src="${root}${r.imageThumb||r.imageSrc}" srcset="${root}${r.imageThumb||r.imageSrc} 400w, ${root}${r.imageSrc} 700w" sizes="(max-width:700px) calc((100vw - 52px)/2), (max-width:1000px) calc((100vw - 88px)/2), 360px" alt="${esc(getLanguage()==='en'?r.word+' — block-world illustration':r.imageAlt)}" width="700" height="560" loading="lazy"><span class="list-badges"><span class="ui-tag">${r.level} · ${r.wordCount} 词</span></span></div><div class="list-copy"><h2>${esc(getLanguage()==='en'?r.word:r.meaning)}</h2><p>${esc(getLanguage()==='en'?(r.sentence.match(/^.*?[.!?](?:\s|$)/)?.[0]||r.sentence):r.description)}</p></div></a>`).join('')}</div>`;let pending=0;const grid=app.querySelector('.readings-grid'),filters=app.querySelector('.reading-level-filters');
app.querySelectorAll('button[data-reading-level]').forEach(button=>button.addEventListener('click',async()=>{
 const level=button.dataset.readingLevel;if(level===readingLevel){++pending;filters.removeAttribute('aria-busy');return}
 const request=++pending;filters.setAttribute('aria-busy','true');
 const selected=[...grid.querySelectorAll('[data-reading-card-level]')].filter(card=>level==='全部'||card.dataset.readingCardLevel===level);
 // Keep controls and cards mounted; prioritize the next row without waiting on it.
 const firstRow=selected.slice(0,innerWidth>1000?3:2).map(card=>card.querySelector('img'));
 firstRow.forEach(img=>{img.loading='eager'});
 // Loading images must not block category selection or its visual feedback.
 firstRow.forEach(img=>{img.decode().catch(()=>{})});
 if(request!==pending||!grid.isConnected||location.hash!=='#readings')return;
 readingLevel=level;const url=new URL(location.href);if(level==='全部')url.searchParams.delete('level');else url.searchParams.set('level',level);
 history.replaceState({...history.state,hhxPath:url.pathname+url.search+url.hash},'',url);
 for(const card of grid.querySelectorAll('[data-reading-card-level]')){
  card.hidden=level!=='全部'&&card.dataset.readingCardLevel!==level;
  const to=new URL(card.href);to.searchParams.delete('back');if(level==='全部')to.searchParams.delete('level');else to.searchParams.set('level',level);card.href=readerHref(to.pathname+to.search);
 }
 for(const item of filters.querySelectorAll('button'))item.setAttribute('aria-pressed',String(item.dataset.readingLevel===level));
 filters.removeAttribute('aria-busy');
}));}


let favoriteFilter=new URLSearchParams(location.search).get('filter')||'all',wordCache,renderVersion=0;if(!['all',...Object.keys(contentTypes)].includes(favoriteFilter))favoriteFilter='all';
const favoriteLoadingMarkup=document.querySelector('.startup-favorites .favorite-loading-list')?.outerHTML||'';
async function favoritesPage(){
 if(window.hhxLearningFavorites&&!window.hhxLearningFavorites.isReady()){
  ++renderVersion;document.title='收藏夹 · 很好学';
  app.innerHTML=listBack('收藏夹',favoriteReturnHref())+'<section class="favorite-empty-state" role="status"><h2>收藏暂时无法读取</h2><p>其他学习内容可正常浏览，请稍后重试收藏同步。</p><button class="primary" type="button" data-favorites-load-retry>重新加载</button></section>';
  app.querySelector('[data-favorites-load-retry]').onclick=()=>location.reload();return;
 }

 favoriteFilter=new URLSearchParams(location.search).get('filter')||'all';
 if(!['all',...Object.keys(contentTypes)].includes(favoriteFilter))favoriteFilter='all';
 const version=++renderVersion;
 document.title='收藏夹 · 很好学';
 const filters=[['all','全部'],...Object.entries(contentTypes).map(([key,v])=>[key,v.label])];
 app.innerHTML=listBack('收藏夹',favoriteReturnHref())+`<nav class="favorite-filters ui-filter-group favorite-type-filters" aria-label="收藏内容类型">${filters.map(([key,label])=>`<button class="ui-tag ui-tag--filter" type="button" aria-pressed="${favoriteFilter===key}" data-filter="${key}">${label}<span>${key==='all'?collectionCount():readCollection(key).length}</span></button>`).join('')}</nav><div id="favorite-items" aria-live="polite"></div>`;
 app.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{
  favoriteFilter=button.dataset.filter;
  const url=new URL(location.href);url.searchParams.set('filter',favoriteFilter);
  history.replaceState({...history.state,hhxPath:url.pathname+url.search+url.hash},'',url);
  favoritesPage().then(()=>app.querySelector(`[data-filter="${favoriteFilter}"]`)?.focus());
 }));
 const target=document.getElementById('favorite-items');
 let words=[];
 if((favoriteFilter==='all'||favoriteFilter==='words')&&readCollection('words').length){
  target.setAttribute('aria-busy','true');
  target.innerHTML=favoriteLoadingMarkup;
  try{
   const ids=readCollection('words');const key=ids.join(',');if(wordCache?.key!==key){const chunks=[];for(let i=0;i<ids.length;i+=50)chunks.push(ids.slice(i,i+50));wordCache={key,promise:Promise.all(chunks.map(part=>fetchPreviewJson(root+'content/word-summaries.json?ids='+encodeURIComponent(part.join(','))))).then(parts=>parts.flatMap(p=>p.words))}}
   words=await wordCache.promise;
  }catch{
   wordCache=null;
   if(version===renderVersion){target.removeAttribute('aria-busy');target.innerHTML='<p class="favorite-empty">暂时无法加载，请刷新重试。</p>';translateTree(target)}
   return;
  }
 }
 if(version!==renderVersion||location.hash!=='#favorites')return;
 const entries=[];
 for(const type of Object.keys(contentTypes)){
  if(favoriteFilter!=='all'&&favoriteFilter!==type)continue;
  for(const id of readCollection(type)){
   let item;
   if(type==='words'){
    const c=words.find(c=>c.id===id);
    if(c)item={title:c.word||(getLanguage()==='en'?'Activate to view this saved card':'激活后查看这张收藏卡片'),meaning:getLanguage()==='en'?c.sentence:c.meaning,image:root+'thumbs/'+c.id+'.webp',href:root+'reader/?topic=words&id='+encodeURIComponent(id)};
   }else if(type==='readings'){
    const c=readingSamples.find(c=>'reading-'+c.id===id);
    if(c)item={title:c.word,meaning:getLanguage()==='en'?c.sentence:c.meaning,image:root+(c.imageThumb||c.imageSrc),href:root+'reader/?topic=readings&id='+c.id};
   }else{
    const c=phrases.find(c=>'phrase-'+c[1]===id);
    if(c)item={title:c[2]||(getLanguage()==='en'?'Activate to view this saved phrase':'激活后查看这句收藏对话'),meaning:getLanguage()==='en'?translate(scenes[c[0]][0]):c[3],image:c[2]?root+phraseImages[c[1]].src.replace(/^\.\.\//,''):root+'scene-covers/'+['greetings','meetup','directions','supplies','building','survival','exploring','rescue','teamwork','connection'][c[0]]+'-thumb.webp',href:root+'reader/?id='+c[1]};
   }
   if(item)entries.push({...item,type,id});
  }
 }
 target.removeAttribute('aria-busy');
 target.innerHTML=entries.length?`<div class="favorite-list">${entries.map((e,i)=>`<article class="favorite-row" data-content-type="${e.type}"><a href="${esc(favoriteItemHref(e.href))}"><img src="${esc(e.image)}" alt="" width="80" height="64"><div class="favorite-row-copy"><div class="favorite-title-line"><h2>${esc(e.title)}</h2>${favoriteFilter==='all'?`<span class="favorite-type ui-tag">${contentTypes[e.type].label}</span>`:''}</div><p>${esc(e.meaning)}</p></div></a><button class="favorite-remove" type="button" data-remove="${i}" title="取消收藏" aria-label="取消收藏 ${esc(e.title)}">${iconMarkup('saved')}</button></article>`).join('')}</div>`:`<section class="favorite-empty-state" aria-label="收藏为空"><div class="favorite-empty-icon">${iconMarkup('saved')}</div><h2>还没有收藏${favoriteFilter==='all'?'内容':contentTypes[favoriteFilter].label}</h2><p>在学习卡片上点按「收藏」，喜欢的内容就会保存在这里。</p><a class="favorite-empty-action" href="${root}#${favoriteFilter==='all'?'home':contentTypes[favoriteFilter].listHash}">${favoriteFilter==='all'?'去探索内容':'去'+contentTypes[favoriteFilter].title}${icon('arrow')}</a></section>`;
 enhance();
 target.querySelectorAll('[data-remove]').forEach(button=>button.addEventListener('click',()=>{const e=entries[Number(button.dataset.remove)];removeCollection(e.type,e.id);favoritesPage()}));
}
function enhance(){sizeResumeThumbnail();app.querySelectorAll('a[href]:not(.back-nav-link)').forEach(a=>{const u=new URL(a.href);if(u.origin===location.origin&&u.pathname===root+'reader/'&&!u.searchParams.has('back')){if(location.hash==='#readings'&&readingLevel!=='全部')u.searchParams.set('level',readingLevel);a.href=readerHref(u.pathname+u.search)}});translateTree(app);[...app.querySelectorAll('img')].filter(img=>!img.closest('[hidden]')).forEach((img,i)=>{img.decoding='async';img.loading=i<3?'eager':'lazy';img.fetchPriority=i===0?'high':'auto'})}
function render(){const hash=location.hash.slice(1),isList=['words','all-words','readings','scenes','favorites','tips'].includes(hash);document.body.classList.toggle('topic-list-page',isList);document.body.classList.toggle('favorites-page',hash==='favorites');app.setAttribute('aria-label',hash==='words'?'看图学单词':hash==='readings'?'游戏小百科':hash==='scenes'?'游戏常用对话':hash==='favorites'?'收藏夹':hash==='tips'?'像 App 一样使用':'学习主页');if(hash==='tips'){document.title=translate('像 App 一样使用')+' · '+translate('很好学');app.innerHTML=listBack('像 App 一样使用')+tipsMarkup()}else if(hash==='favorites')favoritesPage();else if(hash==='all-words'){renderWordBrowser(app);return}else if(hash==='words')wordsPage();else if(hash==='readings')readingsPage();else if(hash==='scenes')scenePage();else if(/^phrase\/\d+$/.test(hash))phrasePage(Number(hash.split('/')[1]));else home();enhance();restoreDirectoryScroll();}window.addEventListener('hhx-live-route-change',render);window.addEventListener('hashchange',render);window.addEventListener('popstate',render);window.addEventListener('pageshow',event=>{if(event.persisted)render()});window.addEventListener('hhx-language-change',render);if(!initialWordBrowser||location.hash!=='#all-words')render();

document.documentElement.dataset.learningReady="true";window.dispatchEvent(new Event("hhx-learning-ready"));
