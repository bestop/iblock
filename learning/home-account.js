import {requestTimeout} from './ui/request-timeout.js';
import {formatAccountLabel} from './ui/account-identity.js';
import {installFocusModality} from './ui/focus-modality.js?v=20261023-shared-focus';
installFocusModality();
import {attachCommunity} from './community.js?v=20261023-community-polish';
import {accountHref,openFavorites,navigateTo} from './ui/favorites-navigation.js?v=20261022-context-gloss-v1';
import {iconMarkup as glyph} from './ui/icons.js?v=20261022-context-gloss-v1';
import {getLanguage,setLanguage,translate} from './ui/language.js?v=20261023-add-hhx-desktop';
// Same-origin learning preview account menu; session identity comes only from /api/me.
const isHomepage=location.pathname==='/';
const demoLinks=isHomepage?[...document.querySelectorAll('a[href="/learning/"]')].map(a=>({a,html:a.innerHTML,href:a.href})):[];
const note=document.querySelector('.hero-note'),noteText=note?.textContent
const entry=document.querySelector('nav .nav-auth')
entry.hidden=true;const pending=document.querySelector('.account-state-pending');entry.closest('nav').setAttribute('aria-busy','true')
entry.addEventListener('click',()=>{entry.href=accountHref()});
const more=document.createElement('details');more.className='preview-account preview-more';more.hidden=true;const moreTitle=document.createElement('summary');moreTitle.innerHTML=glyph('more');moreTitle.setAttribute('aria-label','更多');const moreOptions=document.createElement('div');moreOptions.className='preview-account-options ui-menu ui-menu--lg';more.append(moreTitle,moreOptions);
const menu=document.createElement('details');menu.className='preview-account';menu.hidden=true
const label=document.createElement('summary');label.setAttribute('aria-label','账号菜单')
const avatar=new Image(24,24);avatar.src=new URL('./account-avatar-f2d3d7739450.webp',import.meta.url).href;avatar.alt='';const avatarFrame=document.createElement('span');avatarFrame.className='account-avatar';avatarFrame.dataset.avatarThumbnail='true';avatarFrame.setAttribute('aria-hidden','true');avatarFrame.append(avatar);const accountName=document.createElement('span');accountName.className='account-name';const arrowHost=document.createElement('span');arrowHost.innerHTML=glyph('chevron');const arrow=arrowHost.firstElementChild;arrow.classList.add('account-chevron');label.append(avatarFrame,accountName,arrow)
const options=document.createElement('div');options.className='preview-account-options ui-menu ui-menu--lg';
const account=document.createElement('a');account.href=accountHref('account');
const favorites=document.createElement('a');favorites.href=new URL('./',import.meta.url).pathname+'#favorites';
const tips=document.createElement('a');tips.href=new URL('./',import.meta.url).pathname+'#tips';tips.addEventListener('click',e=>{e.preventDefault();menu.open=false;more.open=false;navigateTo(tips.href)});
const language=document.createElement('details');language.className='language-settings';
const languageTitle=document.createElement('summary');languageTitle.className='language-summary';
const languageOptions=document.createElement('div');languageOptions.className='language-options';languageOptions.setAttribute('role','group');
const zh=document.createElement('button'),en=document.createElement('button');zh.type=en.type='button';zh.addEventListener('click',()=>setLanguage('zh'));en.addEventListener('click',()=>setLanguage('en'));languageOptions.append(zh,en);language.append(languageTitle,languageOptions);
const logout=document.createElement('button');logout.type='button';
const login=document.createElement('a');login.href=accountHref();
favorites.addEventListener('click',e=>{e.preventDefault();menu.open=false;openFavorites()});for(const a of [account,login])a.addEventListener('click',()=>{a.href=accountHref(a===account?'account':'')});
const feedback=document.createElement('p');feedback.className='preview-account-feedback';feedback.setAttribute('role','status');feedback.hidden=true;
options.append(account,favorites,logout);moreOptions.append(tips,language);menu.append(label,options,feedback);entry.after(menu,more);attachCommunity(menu,options,favorites);
function labels(){const t=translate;moreTitle.setAttribute('aria-label',getLanguage()==='en'?'More':'更多');entry.closest('nav').setAttribute('aria-label',t('主导航'));tips.innerHTML=glyph('tips')+`<span>${t('像 App 一样使用')}</span>`;const brandLabel=document.querySelector('.header .brand strong')||document.querySelector('.brand>span');if(brandLabel)brandLabel.textContent=t('很好学');label.setAttribute('aria-label',t('账号'));if(!accountName.dataset.email)accountName.textContent=t('账号');account.innerHTML=glyph('account')+`<span>${t('我的账号')}</span>`;favorites.innerHTML=glyph('saved')+`<span>${t('收藏夹')}</span>`;languageTitle.innerHTML=glyph('language')+`<span>${t('语言设置')}</span><span class="language-value">${getLanguage()==='en'?'English':'中文'}</span>`;languageOptions.setAttribute('aria-label',t('语言设置'));zh.innerHTML='<span>中文</span>'+(getLanguage()==='zh'?glyph('check'):'');en.innerHTML='<span>English</span>'+(getLanguage()==='en'?glyph('check'):'');zh.setAttribute('aria-pressed',String(getLanguage()==='zh'));en.setAttribute('aria-pressed',String(getLanguage()==='en'));logout.innerHTML=glyph(logout.disabled?'loading':'logout')+`<span>${t(logout.disabled?'正在退出…':'退出登录')}</span>`;logout.querySelector('svg')?.classList.toggle('menu-action-spinner',logout.disabled);login.innerHTML=glyph('account')+`<span>${t('登录 / 注册')}</span>`;entry.textContent=t('登录 / 注册')}
labels();window.addEventListener('hhx-language-change',labels);window.addEventListener('storage',labels);

function render(data){if(isHomepage){const activation=document.querySelector('.hero-activate');if(activation)activation.hidden=!!data.interactive;for(const {a,html,href} of demoLinks){a.href=data.interactive?'/learning/':href;a.innerHTML=html;if(data.interactive){if(a.classList.contains('nav-try'))a.textContent='继续学习';else if(a.closest('.hero-actions')){const text=[...a.childNodes].find(node=>node.nodeType===3);if(text)text.textContent='进入学习主页 ';}}}}pending?.remove();entry.closest('nav').removeAttribute('aria-busy');if(note)note.textContent=data.interactive?'全部专题已开通 · 收藏随账号同步':noteText;entry.hidden=!!data.user;menu.hidden=!data.user;more.hidden=true;if(data.user){options.insertBefore(tips,logout);options.insertBefore(language,logout);more.open=false}else{moreOptions.append(tips,language)}if(!data.user)menu.open=false;account.hidden=!data.user;logout.hidden=!data.user;login.hidden=!!data.user;if(!data.user){accountName.dataset.email='';accountName.textContent=translate('账号');return}accountName.dataset.email='1';accountName.textContent=formatAccountLabel(data.user.email)}
async function refresh(){try{const r=await fetch('/api/me',{credentials:'same-origin',cache:'no-store',signal:requestTimeout(10000)});if(!r.ok)throw Error();render(await r.json())}catch{render({user:null})}}
logout.addEventListener('click',async()=>{logout.disabled=true;logout.setAttribute('aria-busy','true');labels();feedback.hidden=true;try{const r=await fetch('/api/logout',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:'{}'});if(!r.ok)throw Error();location.reload()}catch{feedback.textContent=translate('退出失败，请重试');feedback.hidden=false}finally{logout.disabled=false;logout.removeAttribute('aria-busy');labels()}})
menu.addEventListener('toggle',()=>{if(menu.open)more.open=false});more.addEventListener('toggle',()=>{if(more.open)menu.open=false});document.addEventListener('click',e=>{if(!e.composedPath().includes(menu))menu.open=false;if(!e.composedPath().includes(more))more.open=false});document.addEventListener('keydown',e=>{if(e.key==='Escape'){menu.open=false;more.open=false}});window.addEventListener('pageshow',event=>{if(event.persisted)refresh()})
refresh()
