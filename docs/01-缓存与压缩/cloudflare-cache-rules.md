# Cloudflare 缓存规则配置指南(步骤化,照做即可)

> 目标:CSS / JS / 图片 / 字体 **浏览器缓存 1 年 + 边缘缓存 1 个月**;
> 静态内容 JSON 缓存 1 天;HTML 保持"每次校验"不牺牲更新及时性。
> 全程在 Cloudflare 控制台操作,**源站代码零改动**,10 分钟生效。

## 前置说明(现状实测)

当前全站静态资源返回 `Cache-Control: public, max-age=0, must-revalidate`
—— 浏览器**不缓存任何静态资源**,每次访问都要重新验证。而站内 CSS/JS
已经在用 `?v=日期-描述` 手工管理版本(例如
`/learning/app.js?v=20261025-nav-search&rollback=…`),这正是配合
`immutable` 长缓存的理想形态,只差缓存头。

## 步骤一:静态资源长缓存规则

控制台路径:**Cloudflare Dashboard → 选中 henhaoxue.com → Caching → Cache Rules → Create rule**

1. **Rule name**:`static-assets-1y`
2. **匹配条件(If)**:
   - Field: `Hostname` / Operator: `equals` / Value: `henhaoxue.com`
   - AND,Field: `URI Path` / Operator: `ends with` / Value: `.css`
   - 依次再为 `.js`、`.webp`、`.png`、`.jpg`、`.jpeg`、`.gif`、`.svg`、`.woff2`、`.woff` 添加 OR 条件
     (或在一条规则里用 "ends with any of" 批量填写,Pro 及以上支持多值)
3. **缓存资格(Then)**:
   - Cache eligibility: **Eligible for cache**
   - Edge TTL: Ignore cache-control header and use this TTL → **1 month**
   - Browser TTL: Override origin and use this TTL in browsers → **1 year**
     (Cloudflare 会自动附加 `immutable` 语义的长期缓存;若面板支持
      "Browser TTL: 1 year" 直接选它)
4. 保存部署。

## 步骤二:静态内容 JSON 缓存规则

内容目录 `/learning/content/*.json` 与阅读数据变化频率低,可边缘缓存 1 天:

1. **Rule name**:`content-json-1d`
2. **匹配条件**:
   - Hostname equals `henhaoxue.com`
   - AND URI Path starts with `/learning/content/`
   - AND URI Path ends with `.json`
3. **缓存资格**:
   - Cache eligibility: **Eligible for cache**
   - Edge TTL: **1 day**
   - Browser TTL: **1 day**

> 注意:此规则会让目录数据在边缘滞留最长 1 天。发布新内容后需要立即生效时,
> 在 Cloudflare 面板 **Caching → Configuration → Purge → Custom purge**
> 按 URL 清除对应 JSON 即可。

## 步骤三:HTML 保持短缓存(可选,推荐)

首页当前是 `Cache-Control: no-store`,对回访体验略激进。可建一条规则:

1. **Rule name**:`html-swr`
2. **匹配条件**:Hostname equals `henhaoxue.com` AND
   URI Path **不以上述任何静态扩展名结尾**(用 "not ends with" 组合,或直接排除 `/api/`)
3. **设置**:
   - Edge TTL: **5 minutes**(HTML 变更最多 5 分钟全网生效)
   - Browser TTL: **Respect origin**(尊重源站,保持 `no-store` / `max-age=0`)
   - 如面板支持,开启 **stale-while-revalidate**(Edge TTL 高级选项内)

> 若不想动 HTML,保持现状也完全可以,本步骤收益是首次回源延迟略降。

## 步骤四:验证

```bash
# 1. 静态资源应看到 cf-cache-status: HIT 且 cache-control 带 1 年
curl -sI -H "Accept-Encoding: br" "https://henhaoxue.com/learning/app.js?v=20261025-nav-search" \
  | grep -iE "cf-cache-status|cache-control|content-encoding"

# 2. 浏览器验证:DevTools → Network → 第二次刷新 CSS/JS 应显示
#    "(disk cache)" 或 "(memory cache)",而非 304/200
```

预期变化:

| 资源 | 现状 | 配置后 |
|---|---|---|
| CSS/JS/图片 | `max-age=0`,每次回源验证 | `max-age=31536000`,回访零请求 |
| 内容 JSON | 不缓存 | 边缘 1 天 + 浏览器 1 天 |
| HTML | `no-store` | 保持不变(或 5 分钟边缘缓存) |
| 回访请求数 | 每页 20+ | **≤ 5**(仅 HTML + 新资源) |

## 步骤五:发布新版本时

源站资源 URL 已带 `?v=YYYYMMDD-xxx` 版本串,发新版只要改版本号,
新 URL 自动视为新资源,无需清缓存。若改了内容但 URL 未变(如 directory.json),
用 **Purge by URL** 精准清除。

## 回滚

删除对应 Cache Rule 即恢复原状,即时生效,无残留状态。
