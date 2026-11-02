import {getLanguage,translate} from './language.js';
import {homepageCopy} from './homepage-copy.js';
const originals=new WeakMap(),lastValues=new WeakMap(),attrs=new WeakMap();
const originalTitle=document.title;
let scheduled=false;
const text=value=>homepageCopy[value]??(/^\d+ 句$/.test(value)?value.replace(' 句',' phrases'):translate(value));
function apply(){
 scheduled=false;const english=getLanguage()==='en';document.documentElement.lang=english?'en':'zh-CN';document.title=english?'Henhaoxue | Learn English in a block world':originalTitle;
 const walk=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let node;
 while(node=walk.nextNode()){
  if(node.parentElement?.closest('script,style,[data-no-translate],#hhx-release-notice'))continue;
  if(!originals.has(node)||node.nodeValue!==lastValues.get(node))originals.set(node,node.nodeValue);
  const source=originals.get(node),trimmed=source.trim(),value=english&&trimmed?source.replace(trimmed,text(trimmed)):source;
  lastValues.set(node,value);if(node.nodeValue!==value)node.nodeValue=value;
 }
 for(const el of document.querySelectorAll('[aria-label],img[alt]')){
  let values=attrs.get(el);if(!values){values={};attrs.set(el,values)}
  for(const key of ['aria-label','alt']){if(!el.hasAttribute(key))continue;const current=el.getAttribute(key);if(!values[key]||current!==values[key].last)values[key]={source:current};const v=english?text(values[key].source):values[key].source;values[key].last=v;if(current!==v)el.setAttribute(key,v)}
 }
}
function queue(){if(!scheduled){scheduled=true;requestAnimationFrame(apply)}}
apply();new MutationObserver(queue).observe(document.body,{childList:true,subtree:true,characterData:true});
addEventListener('hhx-language-change',queue);addEventListener('storage',queue);
