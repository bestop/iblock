'use strict';
// POST /api/logout {} -> clears the session cookie
const lib = require('./_lib');

module.exports = lib.guard(async (req, res) => {
  if (req.method !== 'POST') return lib.fail(res, '请求方法不支持。', 405);
  lib.clearSession(res);
  return lib.json(res, { ok: true });
});
