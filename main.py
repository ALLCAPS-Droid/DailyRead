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
            history = []
            
    # 使用 guid (日期+标题) 来作为唯一标识，即使没有独立链接也能精准排重
    existing_guids = {item.get('guid', '') for item in history}
    new_items_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            list_url = "https://saduck.top/my/dailyRead.html"
            print(f"正在访问文章列表页: {list_url}")
            page.goto(list_url, wait_until="networkidle", timeout=30000)
            
            try:
                page.wait_for_selector(".article-meta", timeout=15000)
            except:
                print("未能找到文章卡片，页面可能加载缓慢。")
                return history, 0

            # 🌟 关键修复 1：提取列表页的卡片基本信息（不找链接了）
            cards_info = page.evaluate("""
                () => {
                    let results = [];
                    let metas = document.querySelectorAll('.article-meta');
                    metas.forEach((meta, index) => {
                        let card = meta.parentElement;
                        let dateEl = meta.querySelector('.article-date');
                        let dateText = dateEl ? dateEl.innerText.trim() : '';
                        
                        let titleEl = card.querySelector('.title, h2, h3, h4, .text-lg');
                        let titleText = titleEl ? titleEl.innerText.trim() : `每日晨读_${index}`;
                        
                        results.push({ index: index, date: dateText, title: titleText });
                    });
                    return results;
                }
            """)
            
            print(f"列表页共发现 {len(cards_info)} 篇文章卡片。")
            
            # 2. 反向遍历，保证最新的排在 RSS 最前面
            for info in reversed(cards_info):
                # 构建唯一标识
                clean_date = info['date'].replace(' ', '') if info['date'] else datetime.date.today().isoformat()
                unique_guid = f"{clean_date}-{info['title']}"
                
                if unique_guid in existing_guids:
                    print(f"跳过已存在记录: {unique_guid}")
                    continue
                    
                print(f"发现新文章，正在模拟鼠标点击进入: {unique_guid}")
                try:
                    # 确保我们在列表页
                    if page.url != list_url:
                        page.goto(list_url, wait_until="networkidle")
                        page.wait_for_selector(".article-meta", timeout=10000)
                    
                    # 🌟 关键修复 2：模拟真实人类点击该卡片
                    page.evaluate(f"""
                        (idx) => {{
                            let meta = document.querySelectorAll('.article-meta')[idx];
                            if(meta && meta.parentElement) {{
                                meta.parentElement.click();
                            }}
                        }}
                    """, info['index'])
                    
                    # 等待文章渲染出来 (给 3 秒钟动画和请求时间)
                    page.wait_for_timeout(3000)
                    
                    current_link = page.url
                    
                    # 在详情页提取完整格式的 HTML
                    detail = page.evaluate("""
                        () => {
                            let titleEl = document.querySelector('h1') || document.querySelector('.title');
                            let title = titleEl ? titleEl.innerText.trim() : '';
                            
                            let metaEl = document.querySelector('.article-meta') || document.querySelector('.read-time');
                            let metaText = metaEl ? metaEl.innerText.replace(/\\n/g, ' | ') : '';
                            
                            let contentEl = document.querySelector('.vp-doc') || document.querySelector('.content') || document.querySelector('.el-dialog__body');
                            if(contentEl) {
                                let pager = contentEl.querySelector('.el-pagination');
                                if(pager) pager.remove();
                            }
                            let contentHtml = contentEl ? contentEl.innerHTML : '';
                            
                            return { title, metaText, contentHtml };
                        }
                    """)
                    
                    # 如果详情页没抓到标题，就用列表页的
                    final_title = detail['title'] if detail['title'] else info['title']
                    final_meta = detail['metaText'] if detail['metaText'] else info['date']
                    
                    if detail['contentHtml'] and len(detail['contentHtml'].strip()) > 10:
                        now = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
                        
                        # 3. RSS 专属 HTML 排版
                        beautiful_html = f"""
                        <blockquote>
                            <p>
                                <strong>🏷️ 标签/时间：</strong> {final_meta} <br/>
                                <strong>🔗 原文链接：</strong> <a href="{current_link}">点击在网页查看</a>
                            </p>
                        </blockquote>
                        <hr/>
                        <br/>
                        {detail['contentHtml']}
                        """
                        
                        history.insert(0, {
                            "title": f"[{clean_date}] {final_title}",
                            "link": current_link,
                            "description": beautiful_html,
                            "pubDate": now,
                            "guid": unique_guid
                        })
                        new_items_count += 1
                        existing_guids.add(unique_guid)
                    else:
                        print(f"警告：文章内容提取为空。")
                        
                except Exception as inner_e:
                    print(f"处理第 {info['index']} 篇文章时发生异常: {inner_e}")
                    
        except Exception as e:
            print(f"抓取主流程发生异常: {e}")
        finally:
            browser.close()
            
    # 4. 【保险栓】保存数据
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
