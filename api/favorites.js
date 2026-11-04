'use strict';
// Favorites sync.
//   GET  /api/favorites[?scope=learning] -> { userId, words: [id...] }   (401 when logged out)
//   POST /api/favorites { userId, wordId, saved: boolean } -> { ok, userId, words }
// `words` holds every saved id: word ids, "reading-*" ids and "phrase-*" ids.
// 409 is returned when the client's userId no longer matches the session
// (the frontend treats it as "account switched").
const lib = require('./_lib');

const WORD_ID_RE = /^[A-Za-z0-9][A-Za-z0-9:._\/-]{0,199}$/;

module.exports = lib.guard(async (req, res) => {
  const sess = lib.sessionOf(req);
  if (!sess) return lib.fail(res, '请先登录后再同步收藏。', 401);
  let user = await lib.getUser(sess.e);
  if (!user) user = await lib.getUser(sess.e, { fresh: true });
  if (!user) return lib.fail(res, '登录状态已失效，请重新登录。', 401);
  if (!lib.interactiveOf(user)) return lib.fail(res, '当前账号的图鉴权限不可用。', 403);
  const uid = lib.publicUser(user).id;

  if (req.method === 'GET') {
    const words = await lib.getFavorites(user.email);
    return lib.json(res, { userId: uid, words });
  }

  if (req.method === 'POST') {
    const body = await lib.readBody(req);
    if (!body) return lib.fail(res, '请求格式有误。');
    if (body.userId !== undefined && body.userId !== uid) {
      return lib.fail(res, '账号已切换，请刷新页面。', 409);
    }
    const wordId = String(body.wordId || '');
    const saved = body.saved;
    if (!WORD_ID_RE.test(wordId)) return lib.fail(res, '收藏对象无效。');
    if (typeof saved !== 'boolean') return lib.fail(res, '请求参数无效。');

    const outcome = await lib.mutateFavorites(user.email, (words) => {
      const set = new Set(words);
      if (saved) {
        if (!set.has(wordId) && set.size >= lib.FAVORITES_CAP) return words; // cap reached
        set.add(wordId);
      } else {
        set.delete(wordId);
      }
      return [...set];
    });
    if (outcome.abort) return lib.fail(res, '收藏同步失败，请重试。', 500);
    return lib.json(res, { ok: true, userId: uid, words: outcome.words });
  }

  return lib.fail(res, '请求方法不支持。', 405);
});
