# 很好学 henhaoxue.com 全站优化部署包

基于 2026-11-02 对全站代码的实测分析(首页、/learning/、/learning/account/、
静态资源与内容 JSON),按「缓存与压缩头 + SEO 基建 + SEO 内容页」三条线产出,
所有文件**可直接部署**,不需要改动现有学习应用代码。

## 一、包结构总览

```
henhaoxue-optimization-kit/
├── README.md                          ← 本文件
├── 01-缓存与压缩/                      ← 方案 A:CF 规则(立即生效)+ 方案 B:源站配置(治本)
│   ├── cloudflare-cache-rules.md      ← Cloudflare 控制台逐步操作(首选,先做这个)
│   ├── _headers                       ← 若源站托管在 Cloudflare Pages / Netlify 用这个
│   ├── nginx-cache.conf               ← 源站为 Nginx 用这个
│   └── node-cache.js                  ← 源站为自研 Node 服务用这个
├── 02-SEO基建/
│   ├── head-meta-homepage.html        ← 首页 <head> 增强片段(OG/Twitter 分享卡 + JSON-LD)
│   ├── robots.txt                     ← 替换现有 robots.txt(保留了原 content-signals 注释)
│   ├── 404.html                       ← 品牌化 HTML 404 页(替换当前 JSON 404)
│   └── robots-original-backup.txt     ← 原站 robots.txt 备份(回滚用)
└── 03-SEO内容页/
    ├── generator.py                   ← 静态页生成器(数据更新后重跑)
    ├── data/
    │   ├── directory.json             ← 抓取于 /learning/content/directory.json(预览版)
    │   └── home-words.json            ← 提取自首页内联的 80 个图鉴单词
    └── site/                          ← 生成的静态站点,整个目录上传到域名根
        ├── sitemap.xml                ← 177 个 URL,放域名根(自动包含)
        └── library/                   ← 176 个静态页 + 共享样式
            ├── assets/library.css
            ├── scenes/                ← 短语专题页
            ├── phrases/               ← 短语详情页
            ├── readings/              ← 阅读详情页 + 总览
            └── words/                 ← 图鉴单词详情页 + 总览
```

## 二、部署步骤(建议顺序)

### 第 1 步 · 缓存(收益最大,10 分钟)

按 `01-缓存与压缩/cloudflare-cache-rules.md` 在 Cloudflare 控制台建 2 条
Cache Rule(静态资源 1 年 + 内容 JSON 1 天)。
若能改源站,再按平台二选一落地 `_headers` / `nginx-cache.conf` /
`node-cache.js`,实现双保险。

验证:
```bash
curl -sI "https://henhaoxue.com/learning/app.js?v=20261025-nav-search" \
  | grep -i cache-control
# 预期: Cache-Control: public, max-age=31536000, immutable
```

### 第 2 步 · 首页分享卡 + 结构化数据

打开 `02-SEO基建/head-meta-homepage.html`,把其中 `<meta>` 与 `<script>` 粘贴到
首页 `<head>` 里现有 `<link rel="canonical">` 之后。
(原 og:image 暂用 180×180 品牌图标;建议做一张 1200×630 封面图后替换,
片段内有注释标注替换位置。)

### 第 3 步 · robots.txt 与 404 页

1. 用 `02-SEO基建/robots.txt` 替换域名根的 robots.txt
   (已保留原文件的 Content Signals 声明,末尾新增 `Allow: /` 和 Sitemap 指向)。
2. 把 `02-SEO基建/404.html` 放到站点根,并让服务器把它作为 404 响应页:
   - Nginx:`error_page 404 /404.html;`(样例已写进 nginx-cache.conf)
   - Node:`serve404` 中间件(见 node-cache.js)
   - Cloudflare Pages:文件名 404.html 自动生效

### 第 4 步 · 上传内容页

把 `03-SEO内容页/site/` **整个目录**的内容上传到域名根(与 /learning/ 平级):
```
site/library/**   →  https://henhaoxue.com/library/**
site/sitemap.xml  →  https://henhaoxue.com/sitemap.xml
```
上传完成后到 Google Search Console / Bing 站长平台提交
`https://henhaoxue.com/sitemap.xml`。

## 三、内容页说明(重要)

生成页共 **176 页**(sitemap 177 URL,含首页),数据全部来自线上公开预览接口,
**没有编造任何课程内容**:

| 类型 | 数量 | 路径 | 数据来源 |
|---|---|---|---|
| 短语专题页 | 3 | /library/scenes/scene-01~03/ | directory.json(预览版仅 3 个专题有数据) |
| 短语详情页 | 30 | /library/phrases/<slug>/ | 同上(200 条中 170 条为空占位,已过滤) |
| 阅读详情页 | 60 | /library/readings/<id>/ | directory.json(全量,10 类 × 6 篇) |
| 单词详情页 | 80 | /library/words/<slug>/ | 首页内联词表(10 类 × 8 词) |
| 总览/索引页 | 3 | /library/words|readings|scenes/ | — |

**为什么不是 270 页**:预览版 directory.json 中短语只有 30 条真实数据
(其余为空字符串占位,需激活解锁);为避免生成空页损害 SEO,已自动跳过。
待完整数据可用后,重新抓取 directory.json 放入 `data/`,重跑生成器即可自动补全:

```bash
cd 03-SEO内容页
python3 generator.py --data data/directory.json --words data/home-words.json \
    --out site --base-url https://henhaoxue.com
```

每页均包含:唯一 H1、title/description、canonical、Open Graph + Twitter 卡、
BreadcrumbList + 页型 Schema(DefinedTerm/Article/CollectionPage)、面包屑、
同专题相关推荐、页脚内链 —— 面向"游戏英语单词/短语"长尾搜索词。

## 四、图片路径备忘

| 资源 | 线上状态 | 用途 |
|---|---|---|
| /learning/phrase-images/*.webp | ✅ 已验证 200 | 短语页配图(已引用) |
| /learning/diamond.webp | ✅ 已验证 200 | favicon |
| /app-icons/diamond-180-v2.png | ✅ 已验证 200 | 默认 og:image |
| /learning/reading-scenes/*.webp | ⚠️ 未验证(抓取时网络超时) | 阅读页配图(默认未启用) |

若确认阅读图可用,重跑生成器加参数:
```bash
python3 generator.py --reading-img-base "/learning/reading-scenes/" ... 
```
阅读页会自动改用真实场景缩略图作 og:image 与页内配图。

## 五、上线检查清单

- [ ] `curl -sI` 静态资源确认 `max-age=31536000, immutable`
- [ ] 分享首页链接到微信/Telegram,出现标题+图标卡片
- [ ] 访问任意不存在路径,看到品牌 404 页且 HTTP 状态码为 404
- [ ] `https://henhaoxue.com/sitemap.xml` 可访问、177 条
- [ ] robots.txt 末尾有 `Sitemap: https://henhaoxue.com/sitemap.xml`
- [ ] Search Console 提交 sitemap,几天后观察"网页已编入索引"数量
- [ ] 随机打开 3 个 /library/ 页面,检查排版与图片

## 六、回滚

| 改动 | 回滚方式 |
|---|---|
| Cloudflare Cache Rules | 删除规则,即时生效 |
| 源站缓存头 | 还原配置文件,reload |
| 首页 meta | 删除粘贴的片段 |
| robots.txt | 用 robots-original-backup.txt 还原 |
| 内容页 | 删除 /library/ 目录与 sitemap.xml;如暂不想下线,可先在 robots.txt 加 `Disallow: /library/` |

## 七、预期效果(基于分析判断,非承诺)

- 回访浏览器请求数:每页 20+ → ≤5(静态资源全部命中本地缓存)
- 社交分享:微信/抖音/小红书/Telegram 外链出现品牌卡片,点击率提升
- 搜索可见性:176 个长尾页面可被收录,覆盖"方块/游戏英语单词怎么说什么"类查询;
  当前全站可索引页面仅首页 1 个
- 404 体验:JSON 错误串 → 品牌页,带回到首页/学习页/图鉴的出口
