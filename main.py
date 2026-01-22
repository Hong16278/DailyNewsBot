import feedparser
import os
import requests
import datetime
from deep_translator import GoogleTranslator

# 初始化翻译器
translator = GoogleTranslator(source='auto', target='zh-CN')

# 配置：RSS 源列表 (可以添加多个)
RSS_FEEDS = [
    {
        "name": "Hacker News (Tech)",
        "url": "https://news.ycombinator.com/rss",
        "max_items": 3,
        "translate": True  # 标记需要翻译的源
    },
    {
        "name": "少数派 (效率/生活)",
        "url": "https://sspai.com/feed",
        "max_items": 3,
        "translate": False
    },
    {
        "name": "36氪 (科技/创投)",
        "url": "https://36kr.com/feed",
        "max_items": 3,
        "translate": False
    }
]

# 配置：飞书/钉钉/Telegram 等 Webhook 地址 (从环境变量获取，保证安全)
# 在 GitHub Actions 的 Secrets 中配置这个变量
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

def get_latest_news():
    """获取所有 RSS 源的最新新闻"""
    all_news = []
    
    for feed_conf in RSS_FEEDS:
        print(f"正在获取 {feed_conf['name']} ...")
        try:
            # feedparser 会自动处理网络请求
            feed = feedparser.parse(feed_conf['url'])
            
            if not feed.entries:
                print(f"  ⚠️ {feed_conf['name']} 未获取到条目 (可能是网络问题或源格式不对)")
                continue

            print(f"  ✅ 成功获取 {len(feed.entries)} 条")
            
            # 取前 N 条
            for entry in feed.entries[:feed_conf['max_items']]:
                title = entry.title
                # 如果需要翻译
                if feed_conf.get('translate'):
                    try:
                        translated_title = translator.translate(title)
                        title = f"{translated_title} ({title})" # 中文 (英文)
                    except Exception as e:
                        print(f"    ⚠️ 翻译失败: {e}")
                
                item = {
                    "source": feed_conf['name'],
                    "title": title,
                    "link": entry.link,
                    "published": entry.get("published", "")[:16] # 截取部分时间字符串
                }
                all_news.append(item)
        except Exception as e:
            print(f"  ❌ 获取 {feed_conf['name']} 失败: {e}")
            
    return all_news

def format_message(news_items):
    """将新闻格式化为发送的消息内容"""
    if not news_items:
        return "今日无重要新闻。"
    
    # 获取当前日期
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    msg_lines = [f"📅 {current_date} 每日新闻聚合：\n"]
    
    # 按来源分组或者直接列出 (这里直接列出)
    for idx, item in enumerate(news_items, 1):
        # 清理标题中的换行符
        title = item['title'].replace('\n', ' ').strip()
        msg_lines.append(f"{idx}. [{item['source']}] {title}")
        msg_lines.append(f"   🔗 {item['link']}\n")
    
    return "\n".join(msg_lines)

def send_notification(content):
    """发送通知 (模拟发送，或者实际调用 Webhook)"""
    if not WEBHOOK_URL:
        print("⚠️ 未配置 WEBHOOK_URL 环境变量。仅打印内容到控制台：")
        print("-" * 30)
        print(content)
        print("-" * 30)
        print("提示：如果你想发送到手机，请在 GitHub Secrets 中配置 WEBHOOK_URL")
        return

    # 钉钉 (DingTalk) 机器人格式
    # 注意：你需要设置钉钉机器人的安全关键词，建议设为 "新闻"
    payload = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                print("✅ 消息推送成功！")
            else:
                print(f"❌ 推送失败: {result}")
        else:
            print(f"❌ 网络请求失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 发送出错: {e}")

def main():
    print("🚀 自动推文发送器启动...")
    news = get_latest_news()
    message = format_message(news)
    send_notification(message)
    print("🏁 任务完成。")

if __name__ == "__main__":
    main()
