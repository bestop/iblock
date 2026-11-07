#!/usr/bin/env python3
"""Live end-to-end test of the mirror's own API on https://bk.hijoe.net."""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request

BASE = "https://bk.hijoe.net"
GH = "https://api.github.com"
GH_TOKEN = os.environ["GH_TOKEN"]
GH_REPO = "bestop/iblock-data"
EMAIL = f"live-qa-{int(time.time())}@test.local"
PASSWORD = "live-qa-password-456"
cookie = None
passed = failed = 0


def ok(label, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ok   {label}")
    else:
        failed += 1
        print(f"  FAIL {label} :: {extra}")


def req(path, method="GET", body=None, use_cookie=True, headers=None):
    global cookie
    h = dict(headers or {})
    if body is not None:
        h["Content-Type"] = "application/json"
    if use_cookie and cookie:
        h["Cookie"] = cookie
    r = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                               method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            sc = resp.headers.get("Set-Cookie")
            if sc:
                cookie = sc.split(";")[0]
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


print("live test on", BASE, "account:", EMAIL)

# 0 static sanity
st, html = None, None
with urllib.request.urlopen(BASE + "/", timeout=30) as resp:
    st, html = resp.status, resp.read().decode()
ok("GET / -> 200", st == 200)
ok("canonical -> bk.hijoe.net", 'rel="canonical" href="https://bk.hijoe.net/"' in html, "canonical missing")
ok("no origin URL in homepage", "henhaoxue.com" not in html)
ok("og:url -> bk.hijoe.net", 'property="og:url" content="https://bk.hijoe.net/"' in html)
for path in ("/sitemap.xml", "/robots.txt", "/learning/", "/account/", "/learn/"):
    with urllib.request.urlopen(BASE + path, timeout=30) as resp:
        body = resp.read().decode()
    if path == "/robots.txt":
        ok(f"GET {path}", "Sitemap: https://bk.hijoe.net/sitemap.xml" in body)
    elif path == "/sitemap.xml":
        ok(f"GET {path}", "<loc>https://bk.hijoe.net/</loc>" in body and "henhaoxue.com" not in body)
    else:
        ok(f"GET {path} -> 200", resp.status == 200)

# 1 guest API state
st, j = req("/api/me")
ok("me guest -> 200 {user:null}", st == 200 and j.get("user") is None, f"{st} {j}")
st, j = req("/api/favorites")
ok("favorites guest -> 401", st == 401, f"{st} {j}")

# 2 register
st, j = req("/api/email-code", "POST", {"email": EMAIL, "purpose": "register", "code": "LIVE-ORDER-1"})
code = (j.get("message") or "").match if False else None
m = re.search(r"验证码：(\d{6})", j.get("message") or "")
ok("email-code -> demo code in message", st == 200 and m, json.dumps(j)[:160])
challenge, code = j.get("challengeId"), m.group(1)
st, j = req("/api/register", "POST", {"email": EMAIL, "password": PASSWORD, "emailCode": code,
                                      "challengeId": challenge, "code": "LIVE-ORDER-1"})
ok("register -> 200 + user + interactive", st == 200 and j.get("user", {}).get("email") == EMAIL and j.get("interactive") is True, f"{st} {json.dumps(j)[:200]}")
uid = j.get("user", {}).get("id")
ok("session cookie captured", bool(cookie), cookie)

# 3 me / favorites
st, j = req("/api/me")
ok("me -> logged in", st == 200 and j["user"]["id"] == uid and j["interactive"] is True)
for word in ("apple", "reading-01", "phrase-hello"):
    st, j = req("/api/favorites", "POST", {"userId": uid, "wordId": word, "saved": True})
    ok(f"favorite add {word}", st == 200 and j.get("ok") is True, f"{st} {j}")
st, j = req("/api/favorites")
ok("favorites list -> 3", st == 200 and len(j.get("words", [])) == 3, f"{st} {j}")
st, j = req("/api/favorites", "POST", {"userId": uid, "wordId": "apple", "saved": False})
st, j = req("/api/favorites")
ok("favorites list -> 2 after remove", len(j.get("words", [])) == 2, str(j))

# 4 release notice
st, j = req("/api/release-notice")
ok("notice -> dismissed:false", st == 200 and j.get("dismissed") is False, f"{st} {j}")
st, j = req("/api/release-notice", "POST", {"version": "learning-20261026"})
st, j = req("/api/release-notice")
ok("notice -> dismissed:true after POST", j.get("dismissed") is True, str(j))

# 5 logout / login
st, j = req("/api/logout", "POST", {})
ok("logout -> 200", st == 200, f"{st} {j}")
st, j = req("/api/me")
ok("me after logout -> guest", st == 200 and j.get("user") is None)
st, j = req("/api/login", "POST", {"email": EMAIL, "password": PASSWORD})
ok("login -> 200", st == 200 and j.get("user", {}).get("email") == EMAIL, f"{st} {json.dumps(j)[:160]}")

# 6 recover
st, j = req("/api/email-code", "POST", {"email": EMAIL, "purpose": "recover"})
m = re.search(r"验证码：(\d{6})", j.get("message") or "")
st, j = req("/api/recover", "POST", {"email": EMAIL, "password": "live-qa-password-999",
                                     "emailCode": m.group(1), "challengeId": j.get("challengeId")})
ok("recover -> 200", st == 200, f"{st} {json.dumps(j)[:160]}")
st, j = req("/api/login", "POST", {"email": EMAIL, "password": "live-qa-password-999"})
ok("login with new password -> 200", st == 200, f"{st} {j}")

# 7 cleanup on the data repo
def gh(path, method="GET", payload=None):
    r = urllib.request.Request(f"{GH}/repos/{GH_REPO}/contents/{path}", method=method,
                               headers={"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json", "User-Agent": "qa"},
                               data=json.dumps(payload).encode() if payload else None)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, None

st, j = gh("users.json")
data = json.loads(__import__("base64").b64decode(j["content"]).decode())
if EMAIL in data.get("users", {}):
    del data["users"][EMAIL]
    st2, _ = gh("users.json", "PUT", {"message": f"live-qa cleanup {EMAIL}",
                                      "content": __import__("base64").b64encode(json.dumps(data).encode()).decode(), "sha": j["sha"]})
    ok("cleanup users.json", st2 == 200, str(st2))
md5 = hashlib.md5(EMAIL.encode()).hexdigest()
st, j = gh(f"favorites/{md5}.json")
if st == 200:
    st2, _ = gh(f"favorites/{md5}.json", "DELETE", {"message": f"live-qa cleanup {EMAIL}", "sha": j["sha"]})
    ok("cleanup favorites", st2 == 200, str(st2))

print(f"\nRESULT: {passed} passed, {failed} failed")
raise SystemExit(1 if failed else 0)
