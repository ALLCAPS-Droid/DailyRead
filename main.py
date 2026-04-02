import requests
import re
import json
import datetime
import os

def get_content():
    base_url = "https://saduck.top"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        print("正在访问主页……")
        html_resp = requests.get(f"{base_url}/my/dailyRead.html", headers=headers, timeout=30)
        html = html_resp.text
        
        print("正在寻找 JS 数据文件路径……")
        # 尝试匹配 JS 路径
        js_match = re.search(r'/assets/my_dailyRead\.md\.[a-zA-Z0-9_-]+\.lean\.js', html)
        if not js_match:
            print("错误：在页面中没找到数据 JS 文件的链接！")
            return None, None
        
        js_path = js_match.group(0)
        js_url = base_url + js_path
        print(f"找到数据源 URL: {js_url}")
        
        js_raw = requests.get(js_url, headers=headers, timeout=30).text
        print("正在解析 JS 内容……")
        
        # 提取 JSON.parse 里的字符串
        json_str_match = re.search(r"JSON\.parse\('(.*?)'\)", js_raw)
        if not json_str_match:
            print("错误：在 JS 文件里没找到 JSON 数据内容！")
            return None, None
            
        json_str = json_str_match.group(1)
        
        # 转换 Unicode 编码并解析
        data = json.loads(json_str.encode().decode('unicode_escape'))
        title = data.get('title', '每日晨读')
        content = data.get('html', '')
        
        if not content:
            print("错误：解析出的内容为空！")
            return None, None
            
        print(f"成功抓取文章：{title}")
        return title, content
        
    except Exception as e:
        print(f"程序运行中发生异常: {e}")
        return None, None

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
