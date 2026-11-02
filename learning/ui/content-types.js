/** Add a type here; IDs are always scoped by type. No title-based identity. */
export const contentTypes={
 words:{label:'单词',title:'看图学单词',savedKey:'hhx-learning-words-saved',listHash:'words'},
 readings:{label:'阅读',title:'游戏小百科',savedKey:'hhx-learning-readings-saved',listHash:'readings'},
 phrases:{label:'对话',title:'游戏常用对话',savedKey:'hhx-learning-phrases-saved',listHash:'scenes'}
};
export function readCollection(type){if(globalThis.window?.hhxLearningFavorites)return window.hhxLearningFavorites.read(type);try{const raw=JSON.parse(localStorage.getItem(contentTypes[type].savedKey)||'[]');return Array.isArray(raw)?[...new Set(raw.filter(x=>typeof x==='string'))]:[]}catch{return []}}
export function collectionCount(){return Object.keys(contentTypes).reduce((n,t)=>n+readCollection(t).length,0)}
export function removeCollection(type,id){if(globalThis.window?.hhxLearningFavorites){window.hhxLearningFavorites.write(type,readCollection(type).filter(x=>x!==id));return}try{localStorage.setItem(contentTypes[type].savedKey,JSON.stringify(readCollection(type).filter(x=>x!==id)));window.dispatchEvent(new Event('hhx-live-collection-change'))}catch{}}

try{const old=JSON.parse(localStorage.getItem('hhx-learning-saved')||'[]');if(Array.isArray(old)&&old.length&&!localStorage.getItem('hhx-learning-favorites-migrated')){const ids=[...new Set([...readCollection('phrases'),...old.map(x=>typeof x==='number'?'phrase-'+x:String(x))])];localStorage.setItem(contentTypes.phrases.savedKey,JSON.stringify(ids));localStorage.setItem('hhx-learning-favorites-migrated','1')}}catch{}
