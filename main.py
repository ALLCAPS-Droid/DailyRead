import requests
import re
import json
import datetime

def get_content():
    base_url = "https://saduck.top"
    try:
        # 1. 访问主页找到最新的数据 JS 文件
        html = requests.get(f"{base_url}/my/dailyRead.html", timeout=30).text
        js_path = re.search(r'/assets/my_dailyRead\.md\.[a-z0-9A-Z_-]+\.lean\.js', html).group(0)
        
        # 2. 获取并解析 JS 里的内容
        js_raw = requests.get(base_url + js_path, timeout=30).text
        json_str = re.search(r"JSON\.parse\('(.*?)'\)", js_raw).group(1)
        
        # 处理转义并提取 HTML
        data = json.loads(json_str.encode().decode('unicode_escape'))
        return data.get('title', '每日晨读'), data.get('html', '')
    except Exception as e:
        print(f"出错啦: {e}")
        return None, None

def make_rss(title, content):
    now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
    today = datetime.date.today().isoformat()
    
    # 简单的 RSS 模板封装
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

if __name__ == "__main__":
    t, c = get_content()
    if t and c:
        make_rss(t, c)
