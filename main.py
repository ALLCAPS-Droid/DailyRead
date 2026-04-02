import datetime
from playwright.sync_api import sync_playwright

def get_content():
    print("正在启动虚拟浏览器……")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("正在访问目标网页……")
            # 访问网页，并等待网络请求基本完成
            page.goto("https://saduck.top/my/dailyRead.html", wait_until="networkidle", timeout=30000)
            
            print("等待正文渲染……")
            # 关键修复：不要等 .vp-doc 容器，而是等容器里的实质性内容（如段落 p 标签）加载出来
            try:
                page.wait_for_selector(".vp-doc p", timeout=10000)
            except:
                # 如果连 p 标签都没有，强制等 3 秒让 JS 跑完
                page.wait_for_timeout(3000)
            
            # 放弃寻找 h1，直接获取网页原生 title（例如 "每日晨读 | SaDuck - 公考知识库"）
            raw_title = page.title()
            title = raw_title.split('|')[0].strip() if '|' in raw_title else "每日晨读"
                
            # 提取 HTML 正文
            content = page.locator(".vp-doc").inner_html()
            
            # 防御性检查：如果抓到的内容太短，说明没加载出真实内容
            if not content or len(content.strip()) < 50:
                print("错误：抓取到的正文太短或为空，页面可能未完全加载。")
                return None, None
            
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
