'use strict';
// POST /api/redeem { code } -> activates the interactive access for the account.
// On the mirror every non-empty code redeems successfully (demo).
const lib = require('./_lib');

module.exports = lib.guard(async (req, res) => {
  if (req.method !== 'POST') return lib.fail(res, '请求方法不支持。', 405);
  const sess = lib.sessionOf(req);
  if (!sess) return lib.fail(res, '请先登录。', 401);
  const body = await lib.readBody(req);
  if (!body) return lib.fail(res, '请求格式有误。');
  const code = String(body.code || '').trim();
  if (!code || code.length > 64) return lib.fail(res, '请输入有效的兑换码。');

  const outcome = await lib.mutateUser(sess.e, (cur) => {
    if (!cur) return lib.ABORT;
    const next = JSON.parse(JSON.stringify(cur));
    next.interactive = true;
    if (!Array.isArray(next.redeemed)) next.redeemed = [];
    if (!next.redeemed.includes(code)) next.redeemed.push(code);
    next.redeemed_at = new Date().toISOString();
    return next;
  });
  if (outcome.abort) return lib.fail(res, '账号不存在。', 404);
  return lib.json(res, { ok: true, interactive: true });
});
