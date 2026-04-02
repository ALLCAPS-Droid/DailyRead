import datetime
import json
import os
from playwright.sync_api import sync_playwright

def get_articles_and_update_history():
    print("正在启动虚拟浏览器……")
    history_file = "history.json"
    
    # 1. 安全加载本地历史记录
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except json.JSONDecodeError:
            print("警告：本地 history.json 格式损坏，将创建新的记录。")
            history = []
            
    existing_links = {item.get('link', '') for item in history}
    new_items_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("正在访问文章列表页: https://saduck.top/my/dailyRead.html")
            page.goto("https://saduck.top/my/dailyRead.html", wait_until="networkidle", timeout=30000)
            
            try:
                page.wait_for_selector(".article-meta", timeout=15000)
            except:
                print("未能找到文章卡片，页面可能加载缓慢。")
            
            # 🌟 关键修复：扩大搜索范围，避免死等 .vp-doc，直接在主区域找 A 标签
            links = page.evaluate("""
                () => {
                    let results = [];
                    let container = document.querySelector('#VPContent') || document.body;
                    
                    container.querySelectorAll('a').forEach(a => {
                        let href = a.href;
                        // 必须是有效 http 链接，且不能是纯锚点
                        if (href && href.startsWith('http') && !href.includes('#')) {
                            // 排除当前页面自己、以及底部的 el-pagination 翻页组件里的链接
                            let isPagination = a.classList.contains('pager-link') || a.closest('.el-pagination');
                            let isSelf = href === window.location.href || href === window.location.href.split('?')[0];
                            
                            if (!isPagination && !isSelf) {
                                if (!results.includes(href)) {
                                    results.push(href);
                                }
                            }
                        }
                    });
                    return results;
                }
            """)
            
            print(f"列表页共发现 {len(links)} 个潜在文章链接。")
            
            # 2. 遍历链接，深入抓取新文章
            for link in reversed(links): 
                if link in existing_links:
                    print(f"跳过已抓取过的文章: {link}")
                    continue 
                    
                print(f"发现新文章，正在抓取全文: {link}")
                try:
                    page.goto(link, wait_until="networkidle", timeout=20000)
                    page.wait_for_timeout(2000) # 给页面渲染的时间
                    
                    detail = page.evaluate("""
                        () => {
                            let titleEl = document.querySelector('h1') || document.querySelector('.title');
                            let title = titleEl ? titleEl.innerText.trim() : document.title.split('|')[0].trim();
                            
                            let metaEl = document.querySelector('.article-meta') || document.querySelector('.read-time');
                            let metaText = metaEl ? metaEl.innerText.replace(/\\n/g, ' | ') : '每日晨读';
                            
                            // 详情页正文通常在 .vp-doc 里
                            let contentEl = document.querySelector('.vp-doc');
                            if(contentEl) {
                                let pager = contentEl.querySelector('.el-pagination');
                                if(pager) pager.remove();
                            }
                            let contentHtml = contentEl ? contentEl.innerHTML : '';
                            
                            return { title, metaText, contentHtml };
                        }
                    """)
                    
                    if detail['contentHtml'] and len(detail['contentHtml'].strip()) > 10:
                        today = datetime.date.today().isoformat()
                        now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
                        
                        # 3. RSS 专属 HTML 排版
                        beautiful_html = f"""
                        <blockquote>
                            <p>
                                <strong>🏷️ 标签/来源：</strong> {detail['metaText']} <br/>
                                <strong>🔗 原文链接：</strong> <a href="{link}">点击在网页查看</a>
                            </p>
                        </blockquote>
                        <hr/>
                        <br/>
                        {detail['contentHtml']}
                        """
                        
                        history.insert(0, {
                            "title": f"[{today}] {detail['title']}",
                            "link": link,
                            "description": beautiful_html,
                            "pubDate": now,
                            "guid": link
                        })
                        new_items_count += 1
                        existing_links.add(link)
                    else:
                        print(f"警告：文章 {link} 内容过短，已跳过。")
                        
                except Exception as inner_e:
                    print(f"抓取详情页 {link} 发生异常: {inner_e}")
                    
        except Exception as e:
            print(f"抓取主流程发生异常: {e}")
        finally:
            browser.close()
            
    # 4. 【保险栓】
    if len(history) > 0:
        history = history[:30] 
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        print("历史记录已安全保存至 history.json。")
    else:
        print("警告：抓取结束后历史记录为空，取消保存 history.json 以防数据丢失。")
        
    return history, new_items_count

def make_rss(history):
    print("开始生成 atom.xml 订阅源……")
    now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
    
    items_xml = ""
    for item in history:
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
  <title>SaDuck 每日晨读</title>
  <link>https://saduck.top/my/dailyRead.html</link>
  <description>自动抓取的公考晨读列表，包含完整格式、加黑重点与来源信息</description>
  <lastBuildDate>{now}</lastBuildDate>{items_xml}
</channel>
</rss>"""

    with open("atom.xml", "w", encoding="utf-8") as f:
        f.write(rss_template)
    print("atom.xml 写入完成！")

if __name__ == "__main__":
    history, new_count = get_articles_and_update_history()
    
    if history and len(history) > 0:
        make_rss(history)
        print(f"✅ 任务全部完成！本次新增了 {new_count} 篇全文。历史库共存有 {len(history)} 篇文章。")
    else:
        print("❌ 警告：未获取到任何文章且历史库为空，跳过 XML 生成步骤。")
