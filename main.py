import datetime
from playwright.sync_api import sync_playwright

def get_content():
    print("正在启动虚拟浏览器……")
    with sync_playwright() as p:
        # 启动一个无界面的 Chromium 浏览器
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("正在访问目标网页……")
            # 访问网页，并等待网络请求基本完成
            page.goto("https://saduck.top/my/dailyRead.html", wait_until="networkidle", timeout=30000)
            
            print("等待正文渲染……")
            # 等待包含正文的 .vp-doc 容器出现
            page.wait_for_selector(".vp-doc", timeout=10000)
            
            # 提取标题和内容
            title = page.locator("h1").first.inner_text()
            if not title:
                title = "每日晨读"
                
            content = page.locator(".vp-doc").inner_html()
            
            print(f"抓取成功！标题：{title}")
            return title, content
            
        except Exception as e:
            print(f"抓取失败: {e}")
            return None, None
        finally:
            browser.close()

def make_rss(title, content):
    print("正在生成 atom.xml 文件……")
    now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
    today = datetime.date.today().isoformat()
    
    rss_template = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>SaDuck 每日晨读</title>
  <link>https://saduck.top/my/dailyRead.html</link>
  <description>自动抓取的公考晨读内容</description>
  <lastBuildDate>{now}</lastBuildDate>
  <item>
    <title><![CDATA[{today} - {title}]]></title>
    <link>https://saduck.top/my/dailyRead.html?date={today}</link>
    <description><![CDATA[{content}]]></description>
    <pubDate>{now}</pubDate>
    <guid>https://saduck.top/my/dailyRead.html?date={today}</guid>
  </item>
</channel>
</rss>"""
    with open("atom.xml", "w", encoding="utf-8") as f:
        f.write(rss_template)
    print("文件写入完成！")

if __name__ == "__main__":
    t, c = get_content()
    if t and c:
        make_rss(t, c)
    else:
        print("由于没抓到有效内容，跳过 XML 生成步骤。")
