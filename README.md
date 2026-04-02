# DailyRead 📖

基于 GitHub Actions 和 Playwright 的全自动晨读 RSS 生成器。

该项目通过模拟真实浏览器行为，深度抓取目标网站的每日晨读文章。经过强力 DOM 清洗和精美排版后，全自动生成最适合 RSS 阅读器订阅的 `atom.xml` 源。

## ✨ 核心特性

* 🤖 **全自动运行**：依托 GitHub Actions 定时抓取，无需自备服务器。
* 🕸️ **仿生级抓取**：使用 Playwright 完美绕过单页应用 (SPA) 的弹窗和动态路由陷阱。
* 🧹 **纯净排版**：自动剥离导航栏、翻页器、底部按钮及免责声明等冗余元素，采用原生 HTML 表格实现左右分栏的纯净 RSS 排版。
* 💾 **智能记忆**：自动维护 `history.json`，稳定保存最近 30 条记录，防止数据丢失或重复抓取。
* ⚡ **自动发布**：无缝对接 GitHub Pages，抓取完成后自动部署并更新 RSS 链接。

## 📂 目录结构

```text
DailyRead/
├── .github/workflows/
│   └── update.yml      # GitHub Actions 定时任务配置
├── main.py             # 核心抓取、清洗与 RSS 生成脚本
├── history.json        # 历史抓取记录库（自动维护）
└── atom.xml            # 最终的 RSS 订阅源文件（自动生成）

## 🛠️ 如何使用（专属部署）

只需 4 步，即可拥有属于你自己的自动更新订阅源：

1. **Fork 本仓库**：将本项目 Fork 到你的个人 GitHub 账号下。
2. **配置 Actions 权限**：进入仓库的 `Settings` -> `Actions` -> `General`，在最下方的 `Workflow permissions` 中勾选 `Read and write permissions` 并保存。
3. **开启 GitHub Pages**：进入仓库的 `Settings` -> `Pages`，将 `Build and deployment` 下的 Source 设置为 `Deploy from a branch`，Branch 选择 `main` 和 `/(root)` 并保存。
4. **手动触发初次运行**：前往仓库的 `Actions` 页面，点击左侧的 `Auto Update RSS`，点击右侧的 `Run workflow` 按钮进行首次抓取。

🎉 **你的专属 RSS 订阅地址将会是：**
`https://<你的 GitHub 用户名>.github.io/<你的仓库名>/atom.xml`

## ⚠️ 免责声明

本项目仅供 Python 爬虫技术交流与 GitHub Actions 自动化学习使用。文章内容版权归原网站所有，请勿用于高频恶意并发请求或任何商业盈利目的。
