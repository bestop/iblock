// Composite small monochrome SVGs once: translucent strokes otherwise overlap darker.
(()=>{
 if(window.__hhxIconOpacityInstalled)return;window.__hhxIconOpacityInstalled=true;
 const originals=new WeakMap(),pending=new Set();let scheduled=false;
 const rgba=value=>{const m=value.match(/^rgba?\(([^)]+)\)$/);if(!m)return null;const p=m[1].replaceAll(',',' ').replace('/',' ').trim().split(/\s+/).map(Number);return p.length>=3?{rgb:`rgb(${p[0]}, ${p[1]}, ${p[2]})`,alpha:p[3]??1}:null};
 function normalize(svg){if(!svg.isConnected)return;const box=svg.getBoundingClientRect();if(box.width>64||box.height>64)return;const original=originals.get(svg);if(original)for(const key of ['color','stroke','opacity'])svg.style[key]=original[key];const css=getComputedStyle(svg),stroke=rgba(css.stroke),fill=rgba(css.fill);const paint=stroke&&stroke.alpha<1?stroke:null;if(!paint||paint.alpha<=0){originals.delete(svg);return}if(!original)originals.set(svg,{color:svg.style.color,stroke:svg.style.stroke,opacity:svg.style.opacity});svg.style.color=paint.rgb;if(stroke)svg.style.stroke=stroke.rgb;svg.style.opacity=String((Number(css.opacity)||1)*paint.alpha)}
 function add(root){if(root.nodeType!==1&&root.nodeType!==9)return;if(root.matches?.('svg'))pending.add(root);root.querySelectorAll?.('svg').forEach(svg=>pending.add(svg));if(!scheduled){scheduled=true;requestAnimationFrame(()=>{scheduled=false;for(const svg of pending)normalize(svg);pending.clear()})}}
 add(document);new MutationObserver(records=>{for(const r of records){if(r.type==='attributes')add(r.target);else for(const n of r.addedNodes)add(n)}}).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class','stroke','fill','color']});
})();
