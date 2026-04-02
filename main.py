import datetime
import json
import os
from playwright.sync_api import sync_playwright

def get_content():
    print("正在启动虚拟浏览器……")
    articles = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("正在访问目标网页……")
            page.goto("https://saduck.top/my/dailyRead.html", wait_until="networkidle", timeout=30000)
            
            print("等待文章列表加载……")
            # 等待带有时间的 meta 标签出现，证明列表已经渲染完毕
            page.wait_for_selector(".article-meta", timeout=15000)
            
            # 使用 JS 在浏览器内部抓取整个列表
            articles = page.evaluate("""
                () => {
                    let results = [];
                    // 找到所有的文章元数据块
                    let metas = document.querySelectorAll('.article-meta');
                    
                    metas.forEach(meta => {
                        // 往上找父节点，通常这就是单个文章的卡片容器
                        let card = meta.parentElement.parentElement;
                        
                        // 提取日期 (从你发给我的源码里看到 class 是 article-date)
                        let dateEl = meta.querySelector('.article-date');
                        let dateText = dateEl ? dateEl.innerText.trim() : '';
                        
                        // 提取标题 (猜测通常会比较显眼，可能是 h2/h3 或者是最大的 a 标签)
                        let titleEl = card.querySelector('.title, h2, h3, h4, .text-lg'); 
                        let title = titleEl ? titleEl.innerText.trim() : '每日晨读';
                        
                        // 提取链接
                        let aTag = card.querySelector('a');
                        let link = aTag ? aTag.href : window.location.href;
                        
                        // 提取简介 (如果有的话)
                        let contentEl = card.querySelector('.content, .desc, .summary, p');
                        let content = contentEl ? contentEl.innerHTML : '请点击标题前往网站查看。';
                        
                        results.push({
                            title: title,
                            date: dateText,
                            link: link,
                            content: content
                        });
                    });
                    return results;
                }
            """)
            
            print(f"抓取成功！本页共找到 {len(articles)} 篇文章。")
            return articles
            
        except Exception as e:
            print(f"抓取失败: {e}")
            return []
        finally:
            browser.close()

def make_rss(articles):
    print("正在处理历史记录并生成 RSS……")
    now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
    
    # 1. 读取历史记录
    history_file = "history.json"
    history = []
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            
    # 用一个集合来存已经抓过的唯一标识（日期+标题），防止重复
    existing_keys = {f"{item.get('date', '')}-{item['title']}" for item in history}
    
    # 2. 遍历新抓到的这 6 篇文章，把没见过的加入历史
    new_items_count = 0
    # 倒序遍历，保证最新的文章插在最前面时顺序是对的
    for item in reversed(articles):
        # 把 HTML 里的特殊字符清理一下
        clean_date = item['date'].replace(' ', '') if item['date'] else datetime.date.today().isoformat()
        unique_key = f"{clean_date}-{item['title']}"
        display_title = f"[{clean_date}] {item['title']}"
        
        if unique_key not in existing_keys:
            history.insert(0, {
                "title": display_title,
                "date": clean_date,
                "link": item['link'],
                "description": item['content'],
                "pubDate": now,
                "guid": unique_key # 使用唯一标识作为 GUID
            })
            new_items_count += 1
            existing_keys.add(unique_key)
            
    # 3. 只保留最近 30 篇文章的历史
    history = history[:30]
    
    # 4. 把更新后的历史保存起来
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    # 5. 拼装最终的 XML
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
  <title>SaDuck 每日晨读列表</title>
  <link>https://saduck.top/my/dailyRead.html</link>
  <description>自动抓取的公考晨读列表，最高保留 30 条记录</description>
  <lastBuildDate>{now}</lastBuildDate>{items_xml}
</channel>
</rss>"""

    with open("atom.xml", "w", encoding="utf-8") as f:
        f.write(rss_template)
    print(f"文件写入完成！本次新增 {new_items_count} 篇文章，当前源中共有 {len(history)} 篇文章。")

if __name__ == "__main__":
    articles = get_content()
    if articles:
        make_rss(articles)
    else:
        print("由于没抓到有效内容，跳过 XML 生成步骤。")
