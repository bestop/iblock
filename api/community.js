'use strict';
// GET /api/community -> community feature flag.
// The origin keeps this disabled; the mirror mirrors the same response so the
// floating community button in learning/community.js stays hidden, exactly
// like the original site for guests.
module.exports = async function handler(req, res) {
  res.statusCode = 200;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end('{"enabled":false}');
};
