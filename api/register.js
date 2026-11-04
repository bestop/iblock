'use strict';
// POST /api/register { email, password, emailCode, challengeId, code }
//   -> creates the account, signs the session in, { user, interactive }
// `code` is the purchase/order code; on the mirror any non-empty code is accepted.
const lib = require('./_lib');

module.exports = lib.guard(async (req, res) => {
  if (req.method !== 'POST') return lib.fail(res, '请求方法不支持。', 405);
  const body = await lib.readBody(req);
  if (!body) return lib.fail(res, '请求格式有误。');
  const email = lib.normalizeEmail(body.email);
  if (!lib.validEmail(email)) return lib.fail(res, '请输入有效的邮箱地址。');
  const password = String(body.password || '');
  if (password.length < 10) return lib.fail(res, '密码至少需要 10 个字符。');
  if (!String(body.code || '').trim()) return lib.fail(res, '请填写购买订单编号或兑换码。');

  const ch = lib.readChallenge(body.challengeId, 'register');
  if (!ch) return lib.fail(res, '验证码已过期，请重新获取验证码。');
  if (ch.e !== email) return lib.fail(res, '邮箱与验证码不匹配，请重新获取验证码。');
  if (!lib.sameText(ch.c, String(body.emailCode || '').replace(/[\s]/g, ''))) {
    return lib.fail(res, '验证码不正确，请重新输入。');
  }

  const outcome = await lib.mutateUser(email, (cur) => {
    if (cur) return lib.ABORT;
    return lib.newUser(email, password);
  });
  if (outcome.abort) return lib.fail(res, '该邮箱已注册，请直接登录。', 409);

  lib.setSession(res, email);
  return lib.json(res, { user: lib.publicUser(outcome.user), interactive: lib.interactiveOf(outcome.user) });
});
