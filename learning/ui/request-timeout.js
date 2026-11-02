// Older Android WebViews support AbortController but not AbortSignal.timeout.
export function requestTimeout(milliseconds){
 if(typeof AbortSignal!=='undefined'&&typeof AbortSignal.timeout==='function')return AbortSignal.timeout(milliseconds);
 if(typeof AbortController!=='undefined'){
  const controller=new AbortController();setTimeout(()=>controller.abort(),milliseconds);return controller.signal;
 }
 return undefined;
}
