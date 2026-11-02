import {requestTimeout} from './request-timeout.js';
import {iconMarkup} from './icons.js';
import {getLanguage} from './language.js';
import {accountHref} from './favorites-navigation.js';
const base='/learning/';
let confirmedMember=false;
export class PreviewRequestError extends Error{constructor(status){super('Preview request failed');this.status=status}}
// Every request is bounded. Errors keep a retry path instead of silently treating a member as a guest.
export async function fetchPreviewJson(path){
 const url=new URL(path,location.origin);if(new URLSearchParams(location.search).get('trial')==='1')url.searchParams.set('trial','1');
 const transient=new Set([408,425,429,500,502,503,504]);
 for(let attempt=0;attempt<2;attempt++){
  try{
   const response=await fetch(url,{credentials:'same-origin',cache:'no-store',signal:requestTimeout(12000),headers:confirmedMember?{'X-HHX-Expect-Member':'1'}:{}});
   if(!response.ok)throw new PreviewRequestError(response.status);
   return await response.json();
  }catch(error){
   if(error instanceof PreviewRequestError&&!transient.has(error.status))throw error;
   if(attempt===1)throw error;
   // GET only: retry a transient response, interrupted connection or incomplete JSON once.
   await new Promise(resolve=>setTimeout(resolve,250));
  }
 }
}

export const previewAccess=fetchPreviewJson(base+'content/access.json').then(access=>{confirmedMember=!!access.member;return access});
// A directory may finish loading first; keep rejection handled until its reader consumes it.
previewAccess.catch(()=>{});
export function allowedIds(access,kind){return access.member?null:access.policy[kind]||[]}
const english=()=>getLanguage()==='en';
const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function lockedMarkup(back=base){return `<main class="preview-recovery" style="max-width:480px;margin:15vh auto;padding:24px;text-align:center"><h1>${english()?'Activate to continue learning':'激活后继续学习'}</h1><p>${english()?'Try the free lessons first, or activate your purchase to unlock all topics.':'可以先学习免费内容，已购买请登录并激活，解锁全部专题。'}</p><p><a href="${escape(accountHref('account'))}">${english()?'Log in / Activate':'登录 / 激活'}</a></p><a href="${escape(back)}">${english()?'Back to free lessons':'返回免费内容'}</a></main>`}
export function renderPreviewError(target,error){
 const auth=error?.status===401||error?.status===403;
 target.innerHTML=`<section class="preview-recovery preview-recovery--error" role="alert"><span class="preview-recovery-icon">${iconMarkup('error')}</span><h1>${english()?(auth?'Please check your account':'Unable to load this page'):(auth?'请确认账号状态':'暂时无法加载')}</h1><p style="margin:12px 0 20px">${english()?(auth?'Your access has changed. Please log in or activate your account.':'The connection may be slow. Please check your network and try again.'):(auth?'登录或开通状态已变化，请重新登录或激活后继续。':'网络连接可能不稳定，请检查网络后重试。')}</p><div class="preview-recovery-actions"><button type="button" data-preview-retry>${english()?'Try again':'重新加载'}</button> <a href="${auth?escape(accountHref('account')):base+'#home'}">${english()?(auth?'Log in / Activate':'Learning home'):(auth?'登录 / 激活':'返回学习主页')}</a></div></section>`;
 target.querySelector('[data-preview-retry]')?.addEventListener('click',()=>location.reload());
}

// Login/activation and a revoked device must not restore an old entitlement snapshot.
if(typeof window!=='undefined'){
 let checking=false;
 async function recheckAccess(){
  if(checking)return;checking=true;
  try{const access=await fetchPreviewJson(base+'content/access.json');if(!!access.member!==confirmedMember)location.reload()}catch(error){if(error?.status===401||error?.status===403)location.reload()}finally{checking=false}
 }
 // Restore the list immediately; only changed permissions require rebuilding it.
 window.addEventListener('pageshow',event=>{if(event.persisted)void recheckAccess()});
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')void recheckAccess()});
}
