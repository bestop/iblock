'use strict';
// POST /api/recover { email, password, emailCode, challengeId }
//   -> resets the password (email code proves ownership), signs the session in
const lib = require('./_lib');

module.exports = lib.guard(async (req, res) => {
  if (req.method !== 'POST') return lib.fail(res, '请求方法不支持。', 405);
  const body = await lib.readBody(req);
  if (!body) return lib.fail(res, '请求格式有误。');
  const email = lib.normalizeEmail(body.email);
  if (!lib.validEmail(email)) return lib.fail(res, '请输入有效的邮箱地址。');
  const password = String(body.password || '');
  if (password.length < 10) return lib.fail(res, '密码至少需要 10 个字符。');

  const ch = lib.readChallenge(body.challengeId, 'recover');
  if (!ch) return lib.fail(res, '验证码已过期，请重新获取验证码。');
  if (ch.e !== email) return lib.fail(res, '邮箱与验证码不匹配，请重新获取验证码。');
  if (!lib.sameText(ch.c, String(body.emailCode || '').replace(/[\s]/g, ''))) {
    return lib.fail(res, '验证码不正确，请重新输入。');
  }

  const outcome = await lib.mutateUser(email, (cur) => {
    if (!cur) return lib.ABORT;
    const next = JSON.parse(JSON.stringify(cur));
    next.pass = lib.makePasswordRecord(password);
    next.pass_changed_at = new Date().toISOString();
    return next;
  });
  if (outcome.abort) return lib.fail(res, '该邮箱尚未注册。', 404);

  lib.setSession(res, email);
  return lib.json(res, { user: lib.publicUser(outcome.user), interactive: lib.interactiveOf(outcome.user) });
});
