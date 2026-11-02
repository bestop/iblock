import {iconMarkup} from './icons.js?v=20261021-back36';
/** Shared by HTML lists and the React reader; same icon as the code-management page. */
export const backArrowPaths=iconMarkup('back').replace(/^<svg[^>]*>|<\/svg>$/g,'');
export function backLinkMarkup(href='#home',label='返回'){return `<a class="back-nav-link" href="${href}" aria-label="${label}"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${backArrowPaths}</svg></a>`;}
