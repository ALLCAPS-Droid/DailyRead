import datetime
import json
import os
from playwright.sync_api import sync_playwright

def get_content():
    print("正在启动虚拟浏览器……")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("正在访问目标网页……")
            page.goto("https://saduck.top/my/dailyRead.html", wait_until="networkidle", timeout=30000)
            
            print("等待正文渲染……")
            try:
                page.wait_for_selector(".vp-doc p", timeout=10000)
            except:
                page.wait_for_timeout(3000)
            
            raw_title = page.title()
            title = raw_title.split('|')[0].strip() if '|' in raw_title else "每日晨读"
                
            content = page.locator(".vp-doc").inner_html()
            
            if not content or len(content.strip()) < 50:
                print("错误：抓取到的正文太短或为空。")
                return None, None
            
            print(f"抓取成功！标题：{title}")
            return title, content
            
        except Exception as e:
            print(f"抓取失败: {e}")
            return None, None
        finally:
            browser.close()

def make_rss(title, content):
    print("正在处理历史记录并生成 RSS……")
    now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
    today = datetime.date.today().isoformat()
    full_title = f"{today} - {title}"
    guid_link = f"https://saduck.top/my/dailyRead.html?date={today}"
    
    # 1. 读取历史记录
    history_file = "history.json"
    history = []
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            
    # 2. 检查今天的内容是否已经抓过（防止重复运行产生重复文章）
    is_duplicate = False
    if len(history) > 0 and history[0]['title'] == full_title:
        is_duplicate = True
        
    # 3. 如果是新文章，插入到列表最前面
    if not is_duplicate:
        history.insert(0, {
            "title": full_title,
            "link": guid_link,
            "description": content,
            "pubDate": now,
            "guid": guid_link
        })
        
    # 4. 只保留最近 15 篇文章的历史
    history = history[:30]
    
    # 5. 把更新后的历史保存起来
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    # 6. 拼装最终的 XML
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
  <description>自动抓取的公考晨读内容</description>
  <lastBuildDate>{now}</lastBuildDate>{items_xml}
</channel>
</rss>"""

    with open("atom.xml", "w", encoding="utf-8") as f:
        f.write(rss_template)
    print(f"文件写入完成！当前源中共有 {len(history)} 篇文章。")

if __name__ == "__main__":
    t, c = get_content()
    if t and c:
        make_rss(t, c)
    else:
        print("由于没抓到有效内容，跳过 XML 生成步骤。")
