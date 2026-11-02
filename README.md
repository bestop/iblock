# iblock · 很好学 henhaoxue.com 全站代码

henhaoxue.com 的**完整静态站点镜像**(2026-11-02 抓取),已集成 SEO 优化,
仓库根目录即部署根目录 —— 可直接托管到 Vercel / Cloudflare Pages / Netlify /
任意静态服务器。

- 线上预览: https://iblock.vercel.app
- 源站参考: https://henhaoxue.com (所有 canonical / JSON-LD 指向生产域名,
  预览镜像不会被搜索引擎误收录)

## 一、目录结构

```
iblock/
├── index.html                  ← 首页(已注入 OG/Twitter 分享卡 + JSON-LD 结构化数据)
├── learning/                   ← 学习应用(页面 + ES Modules + 内容数据 + 图片)
│   ├── index.html  app.js  …   ← 13 个 JS 模块、9 套 CSS、home-assets 等
│   ├── content/directory.json  ← 内容总数据(四区:scenes/phrases/readings/images)
│   ├── reading-scenes/         ← 阅读场景图(60 张 webp)
│   ├── home-dialogue-images/   ← 首页对话图(30 张)
│   ├── home-assets/            ← 首页素材(缩略图 40 张 + 图标)
│   ├── banner-art/ ui/         ← 横幅图 + 学习页 UI 模块
│   └── account/                ← 账号页(与 /account/ 同源)
├── account/                    ← 账号页(镜像源站双路径)
├── ui/  icons/  app-icons/     ← 设计令牌 CSS、品牌图标
├── library/                    ← 176 个 SEO 内容页(短语/阅读/单词/场景)
├── sitemap.xml                 ← 177 个 URL
├── robots.txt                  ← 原 content-signals + Sitemap 行
├── 404.html                    ← 品牌化 404(Vercel/GH Pages 自动使用)
├── vercel.json                 ← 缓存头(静态资源 immutable 1 年)+ 安全头
└── docs/                       ← 原优化包文档(不参与线上部署)
    ├── 01-缓存与压缩/           ← CF 规则 / _headers / nginx / node 四套方案
    ├── 02-SEO基建/              ← head 片段、robots 原版备份、404 源文件
    └── 03-SEO内容页/            ← generator.py 生成器 + data/ 源数据
                                   (内容数据更新后重跑生成器,输出复制到 library/)
```

## 二、部署

**Vercel(当前已部署)**:Import 本仓库即可,零构建 —— 静态文件直接服务,
`vercel.json` 自动带上缓存与安全头。

**其他平台**:
- Cloudflare Pages / Netlify:直接连仓库;缓存头参考
  `docs/01-缓存与压缩/_headers`(本仓库的 vercel.json 只对 Vercel 生效)。
- Nginx 自托管:参考 `docs/01-缓存与压缩/nginx-cache.conf`。

## 三、内容更新流程

1. 源站 `/learning/content/directory.json` 数据更新(如预览版短语转正)后,
   下载新版 JSON 覆盖 `docs/03-SEO内容页/data/directory.json`;
2. 重跑生成器:
   `python3 docs/03-SEO内容页/generator.py --data docs/03-SEO内容页/data/directory.json --words docs/03-SEO内容页/data/home-words.json --out library --base-url https://henhaoxue.com`
3. 提交新生成的 `library/` 页面与 `sitemap.xml`。

## 四、完整性说明

- 镜像通过 BFS 爬取 + 引用闭包校验:234 个站内引用全部有对应本地文件,0 缺失;
- 155 张图片均已验证文件签名有效;
- `/learning/app.js` 等模块使用根相对路径,镜像可独立运行;
- 唯一保留的外部引用是 canonical/JSON-LD 中的 `https://henhaoxue.com`(SEO 设计)。
