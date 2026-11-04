'use strict';
// Shared helpers for the mirror's own backend (zero-dependency, Node.js runtime).
//
// storage : GitHub Contents API on a private data repo (GH_DATA_REPO)
// session : HMAC-signed JWT in an HttpOnly cookie (also accepts Bearer tokens)
// codes   : stateless signed challenges ({email,purpose,code,exp} + HMAC)

const crypto = require('crypto');

const JWT_SECRET = process.env.JWT_SECRET || '';
const GH_TOKEN = process.env.GH_DATA_TOKEN || '';
const GH_REPO = process.env.GH_DATA_REPO || '';
const DEMO = process.env.MIRROR_DEMO !== '0'; // demo mode: the 6-digit code is returned in the message
const COOKIE = 'hhx_session';
const SESSION_TTL = 30 * 24 * 60 * 60; // seconds
const CHALLENGE_TTL = 15 * 60 * 1000; // ms
const GH_API = 'https://api.github.com';
const FAVORITES_CAP = 5000;
const ABORT = Symbol('abort');

// ---------- responses ----------
function json(res, obj, status = 200, extra = {}) {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    ...extra,
  });
  res.end(JSON.stringify(obj));
}
function fail(res, error, status = 400) { json(res, { error }, status); }
function guard(handler) {
  return async (req, res) => {
    try { return await handler(req, res); }
    catch (e) {
      console.error('api error:', e && e.message);
      return fail(res, '服务暂时不可用，请稍后重试。', 503);
    }
  };
}

// ---------- jwt / session ----------
const b64url = (buf) => Buffer.from(buf).toString('base64url');
function hmac(data) {
  return crypto.createHmac('sha256', JWT_SECRET).update(data).digest('base64url');
}
function signJWT(payload) {
  const head = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = b64url(JSON.stringify(payload));
  return head + '.' + body + '.' + hmac(head + '.' + body);
}
function verifyJWT(token) {
  if (typeof token !== 'string' || !token) return null;
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  const [head, body, sig] = parts;
  const a = Buffer.from(sig);
  const b = Buffer.from(hmac(head + '.' + body));
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  let payload;
  try { payload = JSON.parse(Buffer.from(body, 'base64url').toString('utf8')); } catch { return null; }
  if (!payload || typeof payload.e !== 'string' || (payload.exp || 0) * 1000 < Date.now()) return null;
  return payload;
}
function parseCookies(req) {
  const out = {};
  const raw = req.headers.cookie;
  if (!raw) return out;
  for (const part of String(raw).split(';')) {
    const i = part.indexOf('=');
    if (i > 0) out[part.slice(0, i).trim()] = part.slice(i + 1).trim();
  }
  return out;
}
function sessionOf(req) {
  const auth = req.headers.authorization;
  if (auth && /^Bearer\s+/i.test(auth)) return verifyJWT(String(auth).replace(/^Bearer\s+/i, ''));
  return verifyJWT(parseCookies(req)[COOKIE]);
}
function setSession(res, email) {
  const token = signJWT({ e: email, iat: Math.floor(Date.now() / 1000), exp: Math.floor(Date.now() / 1000) + SESSION_TTL });
  res.setHeader('Set-Cookie', `${COOKIE}=${token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${SESSION_TTL}`);
}
function clearSession(res) {
  res.setHeader('Set-Cookie', `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`);
}

// ---------- request body ----------
function readBody(req) {
  return new Promise((resolve) => {
    if (req.method !== 'POST' && req.method !== 'PUT' && req.method !== 'PATCH') return resolve(null);
    const chunks = [];
    let size = 0;
    let done = false;
    const stop = (v) => { if (!done) { done = true; resolve(v); } };
    req.on('data', (c) => {
      size += c.length;
      if (size > 65536) { stop(null); req.destroy(); }
      else chunks.push(c);
    });
    req.on('end', () => {
      if (done) return;
      if (!chunks.length) return resolve({});
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))); }
      catch { resolve(null); }
    });
    req.on('error', () => stop(null));
  });
}

// ---------- passwords / emails ----------
function hashPassword(password, salt) {
  return crypto.scryptSync(String(password), String(salt), 32, { N: 16384, r: 8, p: 1 }).toString('hex');
}
function makePasswordRecord(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  return { salt, hash: hashPassword(password, salt) };
}
// constant-time string comparison (hash first to normalize length)
function sameText(a, b) {
  const ha = crypto.createHash('sha256').update(String(a == null ? '' : a)).digest();
  const hb = crypto.createHash('sha256').update(String(b == null ? '' : b)).digest();
  return crypto.timingSafeEqual(ha, hb);
}
const EMAIL_RE = /^[^\s@]{1,64}@[^\s@]+\.[^\s@]{2,}$/;
const normalizeEmail = (v) => String(v == null ? '' : v).trim().toLowerCase();
const validEmail = (v) => EMAIL_RE.test(v);
const emailKey = (email) => crypto.createHash('md5').update(String(email)).digest('hex');

// ---------- challenges (stateless signed email codes) ----------
function makeChallenge(email, purpose, code) {
  const body = b64url(JSON.stringify({ e: email, p: purpose, c: code, x: Date.now() + CHALLENGE_TTL }));
  return body + '.' + hmac(body);
}
function readChallenge(challengeId, purpose) {
  if (typeof challengeId !== 'string' || !challengeId) return null;
  const i = challengeId.lastIndexOf('.');
  if (i <= 0) return null;
  const body = challengeId.slice(0, i);
  const sig = challengeId.slice(i + 1);
  const a = Buffer.from(sig);
  const b = Buffer.from(hmac(body));
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  let p;
  try { p = JSON.parse(Buffer.from(body, 'base64url').toString('utf8')); } catch { return null; }
  if (!p || (p.x || 0) < Date.now()) return null;
  if (purpose && p.p !== purpose) return null;
  return p;
}

// ---------- GitHub storage ----------
const cache = new Map(); // path -> {t, sha, data}
const CACHE_TTL = 10000;

function ghHeaders() {
  return {
    Authorization: `Bearer ${GH_TOKEN}`,
    Accept: 'application/vnd.github+json',
    'User-Agent': 'iblock-mirror-api',
    'Content-Type': 'application/json',
  };
}

async function ghGet(path, fresh = false) {
  const hit = cache.get(path);
  if (!fresh && hit && Date.now() - hit.t < CACHE_TTL) return hit;
  const r = await fetch(`${GH_API}/repos/${GH_REPO}/contents/${path}`, { headers: ghHeaders() });
  if (r.status === 404) { cache.set(path, { t: Date.now(), sha: null, data: null }); return cache.get(path); }
  if (!r.ok) throw new Error(`gh_get_${r.status}`);
  const j = await r.json();
  let data = null;
  try { data = JSON.parse(Buffer.from(j.content || '', 'base64').toString('utf8')); } catch { data = null; }
  cache.set(path, { t: Date.now(), sha: j.sha, data });
  return cache.get(path);
}

async function ghPut(path, data, sha) {
  const body = {
    message: `data: ${path}`,
    content: Buffer.from(JSON.stringify(data)).toString('base64'),
  };
  if (sha) body.sha = sha;
  const r = await fetch(`${GH_API}/repos/${GH_REPO}/contents/${path}`, {
    method: 'PUT', headers: ghHeaders(), body: JSON.stringify(body),
  });
  if (r.status === 409) return null; // concurrent write -> caller retries
  if (!r.ok) throw new Error(`gh_put_${r.status}`);
  const j = await r.json();
  const entry = { t: Date.now(), sha: (j.content && j.content.sha) || null, data };
  cache.set(path, entry);
  return entry;
}

// users.json shape: { users: { [email]: userRecord } }
// fresh=true bypasses the per-instance cache (multi-instance consistency:
// another lambda may have just written a new password / new account).
async function getUser(email, { fresh = false } = {}) {
  const store = await ghGet('users.json', fresh);
  const users = store && store.data && store.data.users ? store.data.users : {};
  return users[email] || null;
}

// fn(currentRecord|null) -> userRecord | ABORT ; retried on write conflict
async function mutateUser(email, fn) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const cur = await ghGet('users.json');
    const data = cur && cur.data && cur.data.users ? JSON.parse(JSON.stringify(cur.data)) : { users: {} };
    if (!data.users) data.users = {};
    const outcome = fn(data.users[email] || null);
    if (outcome === ABORT) return { abort: true, user: data.users[email] || null };
    data.users[email] = outcome;
    const put = await ghPut('users.json', data, cur ? cur.sha : null);
    if (put) return { abort: false, user: outcome };
  }
  throw new Error('gh_conflict');
}

// favorites/<md5(email)>.json shape: { email, words: [id...] }
function favPath(email) { return `favorites/${emailKey(email)}.json`; }

async function getFavorites(email) {
  const cur = await ghGet(favPath(email));
  return cur && cur.data && Array.isArray(cur.data.words) ? cur.data.words : [];
}

// fn(words) -> new words array | ABORT
async function mutateFavorites(email, fn) {
  const path = favPath(email);
  for (let attempt = 0; attempt < 5; attempt++) {
    const cur = await ghGet(path);
    const data = cur && cur.data ? JSON.parse(JSON.stringify(cur.data)) : { email, words: [] };
    if (!Array.isArray(data.words)) data.words = [];
    const next = fn(data.words);
    if (next === ABORT) return { abort: true, words: data.words };
    data.words = next;
    data.email = email;
    const put = await ghPut(path, data, cur ? cur.sha : null);
    if (put) return { abort: false, words: next };
  }
  throw new Error('gh_conflict');
}

// ---------- user shape ----------
function publicUser(u) {
  return {
    id: emailKey(u.email),
    email: u.email,
    role: u.role || 'member',
    email_verified_at: u.email_verified_at || null,
  };
}
function interactiveOf(u) { return u.interactive !== false; }
function newUser(email, password) {
  return {
    email,
    pass: makePasswordRecord(password),
    role: 'member',
    interactive: true, // mirror grants full learning access to every account
    email_verified_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    notices: {},
  };
}

module.exports = {
  ABORT, DEMO, COOKIE,
  json, fail, guard,
  readBody, sessionOf, setSession, clearSession,
  hashPassword, makePasswordRecord, sameText,
  normalizeEmail, validEmail, emailKey,
  makeChallenge, readChallenge,
  getUser, mutateUser, getFavorites, mutateFavorites, FAVORITES_CAP,
  publicUser, interactiveOf, newUser,
};
