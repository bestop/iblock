'use strict';
// POST /api/login { email, password } -> { user, interactive } + session cookie
const lib = require('./_lib');

module.exports = lib.guard(async (req, res) => {
  if (req.method !== 'POST') return lib.fail(res, '请求方法不支持。', 405);
  const body = await lib.readBody(req);
  if (!body) return lib.fail(res, '请求格式有误。');
  const email = lib.normalizeEmail(body.email);
  if (!lib.validEmail(email)) return lib.fail(res, '请输入有效的邮箱地址。');
  const password = String(body.password || '');
  if (!password) return lib.fail(res, '请输入密码。');
  // fresh read: the record may have been written moments ago by recover/register
  // on another serverless instance
  const user = await lib.getUser(email, { fresh: true });
  if (!user || !user.pass) return lib.fail(res, '邮箱或密码不正确。', 401);
  const ok = lib.sameText(lib.hashPassword(password, user.pass.salt), user.pass.hash);
  if (!ok) return lib.fail(res, '邮箱或密码不正确。', 401);
  lib.setSession(res, email);
  return lib.json(res, { user: lib.publicUser(user), interactive: lib.interactiveOf(user) });
});
