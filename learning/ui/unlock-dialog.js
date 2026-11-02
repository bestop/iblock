import {getLanguage} from './language.js';
import {purchaseHref} from './cover-lock.js';
let disposeCurrent;
/** Shared native dialog for locked covers, word search and reader pagination. */
export function openUnlockDialog({english=getLanguage()==='en',href=purchaseHref,onClose=()=>{}}={}){
 disposeCurrent?.();const trigger=document.activeElement,dialog=document.createElement('dialog');dialog.className='ui-unlock-dialog';dialog.setAttribute('aria-labelledby','ui-unlock-title');
 dialog.innerHTML=`<h2 id="ui-unlock-title" tabindex="-1" autofocus>${english?'Unlock all learning content':'解锁全部学习内容'}</h2><div class="ui-unlock-copy"><p>${english?'Unlock full access to keep exploring.':'开通后，即可学习全部内容。'}</p><p>${english?'Already purchased? Log in and activate your account.':'已经购买？请登录并激活账号。'}</p></div><div class="ui-unlock-actions"><button type="button">${english?'Keep trying':'继续试用'}</button><a target="_blank" rel="noopener noreferrer">${english?'Unlock now':'去解锁'}</a></div>`;
 dialog.querySelector('a').href=href;const overflow=document.documentElement.style.overflow;let disposed=false;
 const dispose=()=>{if(disposed)return;disposed=true;dialog.removeEventListener('close',finish);if(dialog.open)dialog.close();dialog.remove();document.documentElement.style.overflow=overflow;if(trigger?.isConnected)trigger.focus({preventScroll:true});if(disposeCurrent===dispose)disposeCurrent=undefined};
 const finish=()=>{dispose();onClose()};
 dialog.querySelector('button').addEventListener('click',()=>dialog.close());dialog.addEventListener('close',finish);dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close()});
 document.body.append(dialog);document.documentElement.style.overflow='hidden';dialog.showModal();disposeCurrent=dispose;return dispose;
}
let installed=false;
export function installUnlockGate(){if(installed)return;installed=true;document.addEventListener('click',event=>{const link=event.target.closest?.('a[data-unlock]');if(!link||event.button!==0)return;event.preventDefault();event.stopImmediatePropagation();openUnlockDialog()},true)}
