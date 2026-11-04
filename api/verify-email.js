'use strict';
// POST /api/verify-email { challengeId, emailCode } -> { ok: true }
const lib = require('./_lib');

module.exports = lib.guard(async (req, res) => {
  if (req.method !== 'POST') return lib.fail(res, '请求方法不支持。', 405);
  const body = await lib.readBody(req);
  if (!body) return lib.fail(res, '请求格式有误。');

  const ch = lib.readChallenge(body.challengeId, 'verify');
  if (!ch) return lib.fail(res, '验证码已过期，请重新获取验证码。');
  if (!lib.sameText(ch.c, String(body.emailCode || '').replace(/[\s]/g, ''))) {
    return lib.fail(res, '验证码不正确，请重新输入。');
  }

  const outcome = await lib.mutateUser(ch.e, (cur) => {
    if (!cur) return lib.ABORT;
    const next = JSON.parse(JSON.stringify(cur));
    next.email_verified_at = new Date().toISOString();
    return next;
  });
  if (outcome.abort) return lib.fail(res, '账号不存在。', 404);
  return lib.json(res, { ok: true });
});
