import datetime
import json
import os
from playwright.sync_api import sync_playwright

def get_articles_and_update_history():
    print("正在启动虚拟浏览器……")
    history_file = "history.json"
    
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []
            
    existing_guids = {item.get('guid', '') for item in history}
    new_items_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            list_url = "https://saduck.top/my/dailyRead.html"
            print(f"正在访问文章列表页……")
            page.goto(list_url, wait_until="networkidle", timeout=30000)
            
            page.wait_for_selector(".article-meta", timeout=15000)

            cards_info = page.evaluate("""
                () => {
                    let results = [];
                    let metas = document.querySelectorAll('.article-meta');
                    metas.forEach((meta, index) => {
                        let card = meta.parentElement;
                        let dateText = meta.querySelector('.article-date')?.innerText.trim() || '';
                        let titleText = card.querySelector('.title, h2, h3, h4, .text-lg')?.innerText.trim() || `文章_${index}`;
                        results.push({ index: index, date: dateText, title: titleText });
                    });
                    return results;
                }
            """)
            
            print(f"列表页共发现 {len(cards_info)} 篇文章。")
            
            for info in reversed(cards_info):
                clean_date = info['date'].replace(' ', '') if info['date'] else datetime.date.today().isoformat()
                unique_guid = f"{clean_date}-{info['title']}"
                
                if unique_guid in existing_guids:
                    print(f"跳过已存在记录: {unique_guid}")
                    continue
                    
                print(f"正在抓取新文章: {unique_guid}")
                try:
                    # 确保没有对话框挡着
                    page.evaluate("() => { let btn = document.querySelector('.close-btn'); if(btn) btn.click(); }")
                    page.wait_for_timeout(500)

                    # 🌟 修复：通过文本内容来精准定位卡片并点击
                    # 找到包含该文章标题的元素，并点击它的父元素（卡片容器）
                    escaped_title = info['title'].replace("'", "\\'")
                    clicked = page.evaluate(f"""
                        (targetTitle) => {{
                            let elements = Array.from(document.querySelectorAll('.title, h2, h3, h4, .text-lg'));
                            let el = elements.find(e => e.innerText.trim() === targetTitle);
                            if (el && el.parentElement) {{
                                el.parentElement.click();
                                return true;
                            }}
                            return false;
                        }}
                    """, escaped_title)

                    if not clicked:
                        print(f"未能在页面上找到标题为 '{info['title']}' 的卡片，跳过。")
                        continue
                    
                    page.wait_for_timeout(3000)
                    
                    detail = page.evaluate("""
                        () => {
                            let dialog = document.querySelector('.dialog') || document.body;
                            let titleEl = dialog.querySelector('h1') || dialog.querySelector('.dialog-title');
                            let title = titleEl ? titleEl.innerText.trim() : '';
                            
                            let metaSpans = dialog.querySelectorAll('.meta-info span');
                            let source = metaSpans.length >= 1 ? metaSpans[0].innerText.trim() : '';
                            let theme = metaSpans.length >= 2 ? metaSpans[1].innerText.trim() : '';
                            
                            let contentEl = dialog.querySelector('.answer-content') || dialog.querySelector('.content') || dialog.querySelector('.vp-doc');
                            let contentHtml = '';
                            
                            if(contentEl) {
                                let clone = contentEl.cloneNode(true);
                                let junk = ['svg', '.dialog-overlay', '.back-button', '.el-pagination', '.meta-info', '.close-btn'];
                                junk.forEach(s => clone.querySelectorAll(s).forEach(el => el.remove()));
                                
                                clone.querySelectorAll('div, p').forEach(el => {
                                    if(el.innerText.includes('信息来源于网络') || el.innerText.includes('版权问题')) el.remove();
                                });
                                contentHtml = clone.innerHTML.trim();
                            }
                            return { title, source, theme, contentHtml };
                        }
                    """)
                    
                    if detail['contentHtml'] and len(detail['contentHtml']) > 20:
                        now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
                        
                        beautiful_html = f"""
                        <div style="border-bottom: 1px dashed #ccc; padding-bottom: 10px; margin-bottom: 15px;">
                            <table width="100%" style="border: none;">
                                <tr>
                                    <td align="left" style="color: #666;">{detail['source']}</td>
                                    <td align="right" style="color: #666;">{detail['theme']}</td>
                                </tr>
                            </table>
                        </div>
                        <div style="line-height: 1.8;">{detail['contentHtml']}</div>
                        """
                        
                        history.insert(0, {
                            "title": f"[{clean_date}] {detail['title'] or info['title']}",
                            "link": f"{list_url}?guid={unique_guid}",
                            "description": beautiful_html,
                            "pubDate": now,
                            "guid": unique_guid
                        })
                        new_items_count += 1
                        existing_guids.add(unique_guid)
                    
                    # 抓完必须关闭
                    page.evaluate("() => { let btn = document.querySelector('.close-btn'); if(btn) btn.click(); }")
                    page.wait_for_timeout(1000)

                except Exception as inner_e:
                    print(f"处理单篇异常: {inner_e}")
                    
        except Exception as e:
            print(f"主流程异常: {e}")
        finally:
            browser.close()
            
    if len(history) > 0:
        history = history[:30] 
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
    return history, new_items_count

def make_rss(history):
    print(f"正在生成 RSS，共 {len(history)} 篇文章……")
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

    rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>SaDuck 每日晨读</title>
  <link>https://saduck.top/my/dailyRead.html</link>
  <description>纯净版公考晨读</description>
  <lastBuildDate>{now}</lastBuildDate>{items_xml}
</channel>
</rss>"""
    with open("atom.xml", "w", encoding="utf-8") as f:
        f.write(rss)

if __name__ == "__main__":
    h, count = get_articles_and_update_history()
    if h:
        make_rss(h)
        print(f"✅ 完成！新增 {count} 篇。")
