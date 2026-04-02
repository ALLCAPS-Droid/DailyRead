# DailyRead 📖

🦆 **基于 GitHub Actions 和 Playwright 的全自动晨读 RSS 生成器**

这是一个轻量、纯粹且全自动的 RSS 订阅源生成项目。它通过模拟真实浏览器的行为，深度抓取目标网站的每日晨读文章，经过强力清洗和精美排版后，为你生成最适合 RSS 阅读器食用的 `atom.xml` 订阅源。

## ✨ 核心特性

* 🤖 **Serverless 全自动运行**：完全依托 GitHub Actions，无需购买服务器，每天自动准时为您抓取最新文章。
* 🕸️ **仿生级网页交互**：基于 `Playwright` 驱动无界面 Chromium 浏览器，完美绕过 SPA（单页应用）的动态路由与弹窗陷阱，实现自动寻找卡片、点击进入、抓取正文、返回列表的拟人化闭环操作。
* 🧹 **深度 DOM 清洗**：内置强力「网页净化器」，精准剥离目标网页的顶部导航栏、翻页器、SVG 装饰图标、底部按钮、弹窗遮罩及免责声明等冗余元素，只为你保留最纯粹的文章干货。
* 🎨 **原生 RSS 优雅排版**：摒弃不兼容的 CSS 边框和样式，采用原生 HTML `<table>` 和语义化标签进行左右分栏布局，实现「来源」与「主题」的完美对齐，确保在任何 RSS 阅读器（如 Feedly, Inoreader, NetNewsWire）中都能获得极致清爽的阅读体验。
* 💾 **智能历史记忆**：引入双保险机制，自动维护 `history.json` 数据库，稳定保存最近 30 条文章记录，避免重复抓取或因单次网络波动导致的历史数据丢失。
* ⚡ **零配置极速发布**：无缝对接 GitHub Pages，每次 Actions 运行结束后自动触发部署，实现 RSS 链接的实时更新。

## 🚀 它是如何工作的？

1. **定时触发**：GitHub Actions 根据 `.github/workflows/update.yml` 中设定的 Cron 表达式按时唤醒脚本（支持手动触发）。
2. **模拟抓取**：Python 脚本 (`main.py`) 启动虚拟浏览器，进入网站列表页，智能识别新文章卡片并点击进入。
3. **数据处理**：在内存中克隆节点并进行严格的 DOM 清洗，提取正文与元数据，拼装为带表格布局的 HTML 片段。
4. **生成订阅**：将清洗后的内容与本地 `history.json` 比对去重，限制最大保留条数（30 条），最终渲染为标准规范的 `atom.xml`。
5. **自动部署**：Actions 自动 Commit 并 Push 回本仓库，触发内置的 `pages-build-deployment` 工作流，将 `atom.xml` 发布到公网。

## 📂 目录结构

```text
DailyRead/
├── .github/workflows/
│   └── update.yml      # GitHub Actions 自动化工作流配置文件
├── main.py             # 核心抓取、交互、清洗与 RSS 生成脚本
├── history.json        # 历史抓取记录库（由脚本自动生成与维护）
├── atom.xml            # 最终的 RSS 订阅源文件（由脚本自动生成）
└── README.md           # 项目说明文档
