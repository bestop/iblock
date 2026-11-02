/**
 * node-cache.js —— Node.js 源站缓存中间件样例
 *
 * 适用:源站为自研 Node 服务(从 404 返回 JSON 推断可能为此形态)。
 * 提供两种接入方式:Express 中间件 / 原生 http 二次封装,二选一。
 *
 * 用法:
 *   const { cacheHeaders, serve404 } = require('./node-cache');
 *   app.use(cacheHeaders);          // 挂在最前
 *   app.use(serve404);              // 兜底 404 → 品牌页(配套 02-SEO基建/404.html)
 */

'use strict';

const path = require('path');
const fs = require('fs');

// ---------- 规则 ----------
const ONE_YEAR = 31536000;   // 1 年
const ONE_DAY = 86400;       // 1 天

const STATIC_RE = /\.(css|js|mjs|webp|png|jpe?g|gif|svg|ico|woff2?|ttf|otf)$/i;
const CONTENT_JSON_RE = /^\/learning\/content\/.+\.json$/i;

function cacheFor(pathname) {
  if (STATIC_RE.test(pathname)) {
    return { 'Cache-Control': `public, max-age=${ONE_YEAR}, immutable` };
  }
  if (CONTENT_JSON_RE.test(pathname)) {
    return { 'Cache-Control': `public, max-age=${ONE_DAY}` };
  }
  if (pathname === '/404.html') {
    return { 'Cache-Control': 'no-store' };
  }
  return { 'Cache-Control': 'public, max-age=0, must-revalidate' };
}

function applyHeaders(res, pathname) {
  const h = cacheFor(pathname);
  for (const [k, v] of Object.entries(h)) res.setHeader(k, v);
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
}

// ---------- 404 品牌页(替代 JSON 404,返回正确状态码) ----------
const PAGE_404 = (() => {
  try {
    return fs.readFileSync(path.join(__dirname, '..', '02-SEO基建', '404.html'));
  } catch {
    return Buffer.from('<h1>404</h1><p><a href="/">返回很好学</a></p>');
  }
})();

function serve404(req, res, next) {
  res.status(404);
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.send(PAGE_404);
}

// ---------- Express 中间件 ----------
function cacheHeaders(req, res, next) {
  applyHeaders(res, req.path);
  next();
}

// ---------- 原生 http 用法(无 Express 时) ----------
function withCache(handler) {
  return (req, res) => {
    applyHeaders(res, new URL(req.url, 'http://x').pathname);
    handler(req, res);
  };
}

module.exports = { cacheHeaders, serve404, withCache, cacheFor };
