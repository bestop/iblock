'use strict';
// POST /api/email-code { email, purpose: 'register'|'recover'|'verify', code? }
//   -> { challengeId, message, sent }
// The mirror does not deliver real email; in demo mode the 6-digit code is
// returned inside `message` so the whole flow stays exercisable end to end.
const lib = require('./_lib');

module.exports = lib.guard(async (req, res) => {
  if (req.method !== 'POST') return lib.fail(res, '请求方法不支持。', 405);
  const body = await lib.readBody(req);
  if (!body) return lib.fail(res, '请求格式有误。');
  const email = lib.normalizeEmail(body.email);
  if (!lib.validEmail(email)) return lib.fail(res, '请输入有效的邮箱地址。');
  const purpose = String(body.purpose || '');

  const exists = await lib.getUser(email);

  if (purpose === 'register') {
    if (exists) return lib.fail(res, '该邮箱已注册，请直接登录。', 409);
    if (!String(body.code || '').trim()) return lib.fail(res, '请填写购买订单编号或兑换码。');
  } else if (purpose === 'recover') {
    if (!exists) return lib.fail(res, '该邮箱尚未注册。', 404);
  } else if (purpose === 'verify') {
    const sess = lib.sessionOf(req);
    const user = sess && (await lib.getUser(sess.e));
    if (!user) return lib.fail(res, '请先登录后再验证邮箱。', 401);
    if (user.email !== email) return lib.fail(res, '只能验证当前登录账号的邮箱。', 403);
  } else {
    return lib.fail(res, '不支持该验证码用途。');
  }

  const code = String(Math.floor(100000 + Math.random() * 900000));
  const challengeId = lib.makeChallenge(email, purpose, code);
  const tail = lib.DEMO
    ? `（镜像演示模式未接入邮件服务，验证码：${code}，15 分钟内有效）`
    : '，请查收邮件（15 分钟内有效）';
  const message = purpose === 'verify'
    ? `邮箱验证码已生成${tail}`
    : `验证码已发送至 ${email}${tail}`;
  return lib.json(res, { challengeId, message, sent: true });
});
