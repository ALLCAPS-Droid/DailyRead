import datetime
import json
import os
from playwright.sync_api import sync_playwright

def get_articles_and_update_history():
    print("正在启动虚拟浏览器……")
    history_file = "history.json"
    
    # 1. 加载本地历史记录
    history = []
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            
    existing_links = {item.get('link', '') for item in history}
    new_items_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("正在访问文章列表页……")
            # 访问列表页
            page.goto("https://saduck.top/my/dailyRead.html", wait_until="networkidle", timeout=30000)
            page.wait_for_selector(".article-meta", timeout=15000)
            
            # 获取列表上的所有文章链接
            links = page.evaluate("""
                () => {
                    let results = [];
                    // 找到所有卡片里的链接
                    document.querySelectorAll('.vp-doc a').forEach(a => {
                        if(a.href && !results.includes(a.href) && !a.href.includes('#')) {
                            results.push(a.href);
                        }
                    });
                    return results;
                }
            """)
            
            print(f"列表页共发现 {len(links)} 个潜在链接。")
            
            # 2. 遍历链接，只深入抓取「没见过」的新文章
            for link in reversed(links): # 倒序遍历，保证最新的在上面
                if link in existing_links:
                    continue # 如果在历史记录里，直接跳过，节省时间
                    
                print(f"发现新文章，正在进入详情页抓取: {link}")
                try:
                    page.goto(link, wait_until="networkidle", timeout=20000)
                    # 稍微等一下正文渲染
                    page.wait_for_timeout(2000) 
                    
                    # 在详情页提取所有元素（包括加黑标签 <strong> 和来源）
                    detail = page.evaluate("""
                        () => {
                            // 提取标题
                            let titleEl = document.querySelector('h1') || document.querySelector('.title');
                            let title = titleEl ? titleEl.innerText.trim() : document.title.split('|')[0].trim();
                            
                            // 提取来源、主题、日期等元数据 (把换行改成空格)
                            let metaEl = document.querySelector('.article-meta') || document.querySelector('.read-time');
                            let metaText = metaEl ? metaEl.innerText.replace(/\\n/g, ' | ') : '每日晨读';
                            
                            // 提取完整正文 (VitePress 的正文都在 .vp-doc 里，innerHTML 会保留 <strong> 加黑标签)
                            let contentEl = document.querySelector('.vp-doc');
                            // 移除没用的翻页按钮，保持 RSS 干净
                            if(contentEl) {
                                let pager = contentEl.querySelector('.el-pagination');
                                if(pager) pager.remove();
                            }
                            let contentHtml = contentEl ? contentEl.innerHTML : '未找到正文内容';
                            
                            return { title, metaText, contentHtml };
                        }
                    """)
                    
                    if detail['contentHtml']:
                        today = datetime.date.today().isoformat()
                        now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
                        
                        # 3. 核心：给 RSS 穿上排版外衣！
                        # 这里我们用原生的 HTML 加上一点好看的颜色和边框，把来源和主题凸显出来
                        beautiful_html = f"""
                        <div style="background-color: #f4f6f8; padding: 15px; border-left: 5px solid #2081E2; border-radius: 4px; margin-bottom: 20px;">
                            <p style="margin: 0; font-size: 14px; color: #555;">
                                <strong style="color: #333;">🏷️ 标签/来源：</strong> {detail['metaText']} <br/>
                                <strong style="color: #333;">🔗 原文链接：</strong> <a href="{link}">点击在网页查看</a>
                            </p>
                        </div>
                        <div style="font-size: 16px; line-height: 1.8; color: #333;">
                            {detail['contentHtml']}
                        </div>
                        """
                        
                        # 存入历史记录最前面
                        history.insert(0, {
                            "title": f"[{today}] {detail['title']}",
                            "link": link,
                            "description": beautiful_html, # 存入排版好的代码
                            "pubDate": now,
                            "guid": link
                        })
                        new_items_count += 1
                        existing_links.add(link)
                        
                except Exception as inner_e:
                    print(f"抓取详情页 {link} 失败: {inner_e}")
                    
        except Exception as e:
            print(f"抓取列表页失败: {e}")
        finally:
            browser.close()
            
    # 4. 限制并保存历史记录
    history = history[:30]
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
        
    return history, new_items_count

def make_rss(history):
    print("正在生成 atom.xml 文件……")
    now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
    
    items_xml = ""
    for item in history:
        # 注意：这里必须用 <![CDATA[ …… ]]> 把 HTML 包裹起来，阅读器才会正确渲染排版和加黑
        items_xml += f"""
  <item>
    <title><![CDATA[{item['title']}]]></title>
    <link>{item['link']}</link>
    <description><![CDATA[{item['description']}]]></description>
    <pubDate>{item['pubDate']}</pubDate>
    <guid>{item['guid']}</guid>
  </item>"""

    rss_template = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>SaDuck 每日晨读列表 (全文精排版)</title>
  <link>https://saduck.top/my/dailyRead.html</link>
  <description>自动抓取的公考晨读列表，包含完整格式、加黑重点与来源信息</description>
  <lastBuildDate>{now}</lastBuildDate>{items_xml}
</channel>
</rss>"""

    with open("atom.xml", "w", encoding="utf-8") as f:
        f.write(rss_template)

if __name__ == "__main__":
    history, new_count = get_articles_and_update_history()
    if len(history) > 0:
        make_rss(history)
        print(f"✅ 任务完成！本次新增了 {new_count} 篇全文文章。")
    else:
        print("未获取到任何文章。")
