// One moving selection background, shared by word and dialogue category rails.
for(const bar of document.querySelectorAll('#categories,.home-scene-tabs')){
 let frame=0,initialized=false;
 function paint(){frame=0;const selected=bar.querySelector('button[aria-selected="true"],button[aria-pressed="true"]');if(!selected)return;bar.classList.add('has-moving-selection');bar.style.setProperty('--tab-selection-x',selected.offsetLeft+'px');bar.style.setProperty('--tab-selection-y',selected.offsetTop+'px');bar.style.setProperty('--tab-selection-w',selected.offsetWidth+'px');bar.style.setProperty('--tab-selection-h',selected.offsetHeight+'px');if(!initialized){initialized=true;requestAnimationFrame(()=>bar.classList.add('selection-motion-ready'))}}
 function queue(){if(!frame)frame=requestAnimationFrame(paint)}
 new MutationObserver(queue).observe(bar,{subtree:true,childList:true,attributes:true,attributeFilter:['aria-selected','aria-pressed'] ,characterData:true});const sizes=new ResizeObserver(queue);sizes.observe(bar);for(const button of bar.querySelectorAll('button'))sizes.observe(button);window.addEventListener('hhx-language-change',queue);document.fonts.ready.then(queue);queue();
}
