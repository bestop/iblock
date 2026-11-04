'use strict';
// GET /api/me -> { user: {...} | null, interactive: boolean }
const lib = require('./_lib');

module.exports = lib.guard(async (req, res) => {
  const sess = lib.sessionOf(req);
  if (!sess) return lib.json(res, { user: null });
  let user = await lib.getUser(sess.e);
  if (!user) user = await lib.getUser(sess.e, { fresh: true }); // just-written account on another instance
  if (!user) {
    lib.clearSession(res);
    return lib.json(res, { user: null });
  }
  return lib.json(res, { user: lib.publicUser(user), interactive: lib.interactiveOf(user) });
});
