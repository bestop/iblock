import {readingSummary} from './reading-summary.js';
import {installFocusModality} from './focus-modality.js';
// Add future topics here; slide count, dots and controls follow this configuration.
export const accountTopics=[
 {id:'words',title:'看图学单词',description:'看图认识方块，听发音、读例句。',meta:'1245 张单词卡 · 10 大主题',href:'#words'},
 {id:'reading',title:'游戏小百科',description:readingSummary.description,meta:`${readingSummary.count} 篇小知识 · 三档难度`,href:'#readings'},
 {id:'dialogue',title:'游戏常用对话',description:'和队友打招呼，一起用英语冒险。',meta:'200 句常用语 · 10 个场景',href:'#scenes'}
];
export const accountBannerMarkup=`<div class="account-topic-track">${accountTopics.map((t,i)=>`<a class="account-topic-slide" data-topic="${t.id}" href="/learning/${t.href}" aria-label="${t.title}，${t.description}${t.meta}，${i+1}/${accountTopics.length}"><picture class="account-topic-picture"><source media="(min-width:720px) and (orientation:landscape)" srcset="/learning/banner-art/${t.id==='reading'?'reading-complete-portrait-v5':t.id+'-complete-portrait-v2'}.webp" width="1200" height="1500"><source media="(min-width:600px)" srcset="/learning/banner-art/${t.id==='reading'?'reading-complete-wide-v5':t.id+'-complete-mobile-v3'}.webp" width="1600" height="800"><img src="/learning/banner-art/${t.id==='reading'?'reading-complete-mobile-v5':t.id+'-complete-mobile-v3'}.webp" width="1200" height="600" alt="" decoding="async" ${i?'loading="lazy"':''}></picture></a>`).join('')}</div><div class="account-topic-controls"><div class="account-topic-dots" role="group" aria-label="选择专题">${accountTopics.map((t,i)=>`<button type="button" data-slide="${i}" aria-label="查看${t.title}" aria-pressed="${i===0}"><span></span></button>`).join('')}</div></div>`;
const banner=typeof document==='undefined'?null:document.querySelector('#main>.intro');
if(banner){
 installFocusModality();
 banner.id='account-topic-banner';banner.classList.add('account-topic-banner');banner.setAttribute('aria-label','探索学习专题');banner.setAttribute('aria-roledescription','轮播');
 if(!banner.querySelector('.account-topic-track'))banner.innerHTML=accountBannerMarkup;
 const track=banner.querySelector('.account-topic-track'),dots=[...banner.querySelectorAll('[data-slide]')];
 // A non-interactive first-slide copy makes the last-to-first motion continuous.
 const count=accountTopics.length,loop=track.firstElementChild.cloneNode(true);loop.inert=true;loop.setAttribute('aria-hidden','true');loop.dataset.loopClone='true';track.append(loop);
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');let index=0,visible=false,timer,settle,resumeTimer;const hover=matchMedia('(hover:hover) and (pointer:fine)');let hovering=false,pausedUntil=0;
 const paint=()=>{dots.forEach((dot,i)=>dot.setAttribute('aria-pressed',String(i===index)))};
 const go=i=>{const position=i===0&&index===count-1?count:i;index=i;track.scrollTo({left:track.clientWidth*position,behavior:reduced.matches?'instant':'smooth'});paint()};
 const finishScroll=()=>{if(!track.clientWidth)return;const position=Math.round(track.scrollLeft/track.clientWidth);index=position%count;paint();if(position===count&&Math.abs(track.scrollLeft-count*track.clientWidth)<2)track.scrollTo({left:0,behavior:'instant'})};
 function schedule(){clearInterval(timer);if(!visible||document.hidden||hovering||document.activeElement?.matches('input,textarea,select'))return;timer=setInterval(()=>{if(Date.now()>=pausedUntil)go((index+1)%accountTopics.length)},5000)}
 const pauseBriefly=()=>{pausedUntil=Date.now()+8000;clearTimeout(resumeTimer);resumeTimer=setTimeout(schedule,8000);schedule()};
 dots.forEach((dot,i)=>dot.addEventListener('click',()=>{pauseBriefly();go(i)}));
 track.addEventListener('scroll',()=>{clearTimeout(settle);settle=setTimeout(finishScroll,120)},{passive:true});
 track.addEventListener('scrollend',finishScroll,{passive:true});
 track.addEventListener('pointerdown',pauseBriefly,{passive:true});
 banner.addEventListener('mouseenter',()=>{if(hover.matches){hovering=true;schedule()}});banner.addEventListener('mouseleave',()=>{hovering=false;schedule()});
 document.addEventListener('focusin',schedule);document.addEventListener('focusout',()=>queueMicrotask(schedule));document.addEventListener('visibilitychange',schedule);
 const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;schedule()},{threshold:.5});observer.observe(banner);
 window.addEventListener('resize',()=>{track.scrollTo({left:track.clientWidth*index,behavior:'instant'})},{passive:true});
 window.addEventListener('pagehide',()=>{clearInterval(timer);clearTimeout(settle);clearTimeout(resumeTimer);observer.disconnect()},{once:true});paint();
}
