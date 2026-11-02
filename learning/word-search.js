const normalize=value=>String(value??'').normalize('NFKC').toLocaleLowerCase().trim().replace(/\s+/g,' ');
/** Match names only; the browse index deliberately excludes examples, audio and definitions. */
export function filterWords(words,query='',category=''){
 const q=normalize(query),tokens=q.split(' ').filter(Boolean);
 return words.map((word,index)=>{const en=normalize(word.word),zh=normalize(word.meaning);return {word,index,rank:en===q||zh===q?0:en.startsWith(q)||zh.startsWith(q)?1:2,en,zh}}).filter(({word,en,zh})=>(!category||word.category===category)&&tokens.every(t=>en.includes(t)||zh.includes(t))).sort((a,b)=>a.rank-b.rank||a.index-b.index).map(({word})=>word);
}
