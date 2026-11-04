'use strict';
// Release notice (homepage banner) state.
//   GET  /api/release-notice -> { userId: string|null, dismissed: boolean }
//   POST /api/release-notice { version } -> { ok: true }   (account dismissal)
const lib = require('./_lib');
const VERSION_RE = /^[A-Za-z0-9._-]{1,64}$/;

module.exports = lib.guard(async (req, res) => {
  const sess = lib.sessionOf(req);
  if (req.method === 'GET') {
    if (!sess) return lib.json(res, { userId: null });
    const user = await lib.getUser(sess.e);
    if (!user) return lib.json(res, { userId: null });
    const dismissed = !!(user.notices && Object.keys(user.notices).length);
    return lib.json(res, { userId: lib.publicUser(user).id, dismissed });
  }

  if (req.method === 'POST') {
    if (!sess) return lib.json(res, { ok: true }); // guests keep dismissal in localStorage only
    const body = await lib.readBody(req);
    const version = body && String(body.version || '');
    if (!VERSION_RE.test(version)) return lib.fail(res, '请求参数无效。');
    const outcome = await lib.mutateUser(sess.e, (cur) => {
      if (!cur) return lib.ABORT;
      const next = JSON.parse(JSON.stringify(cur));
      if (!next.notices || typeof next.notices !== 'object') next.notices = {};
      next.notices[version] = true;
      return next;
    });
    if (outcome.abort) return lib.json(res, { ok: true });
    return lib.json(res, { ok: true });
  }

  return lib.fail(res, '请求方法不支持。', 405);
});
