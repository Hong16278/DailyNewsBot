import os
import requests
import json

def send(title, content, image_url=None, action_url=None):
    """
    统一消息推送函数
    兼容 WEBHOOK_URL (旧) 和 NOTIFIER_URL (新)
    """
    # 优先使用 WEBHOOK_URL (兼容 main.py 的逻辑)
    webhook_url = os.environ.get("WEBHOOK_URL") or os.environ.get("NOTIFIER_URL")
    
    if not webhook_url:
        print("⚠️ 未配置 WEBHOOK_URL，仅打印日志。")
        print(f"[{title}] {content}")
        if image_url:
            print(f"[图片] {image_url}")
        if action_url:
            print(f"[链接] {action_url}")
        return

    # 1. 钉钉 (DingTalk)
    if "dingtalk.com" in webhook_url:
        send_dingtalk(webhook_url, title, content, image_url, action_url)
    # 2. 其他 (简单文本推送)
    else:
        # 简单回退：只发文本
        final_content = f"{title}\n\n{content}"
        if image_url:
            final_content += f"\n\n![封面]({image_url})"
        if action_url:
            final_content += f"\n\n[链接]({action_url})"
            
        try:
            # 尝试推送到通用 webhook (假设是 json body)
            payload = {"content": final_content, "text": final_content, "message": final_content}
            requests.post(webhook_url, json=payload, timeout=10)
            print("✅ 消息已推送到 Webhook")
        except Exception as e:
            print(f"❌ 推送失败: {e}")

def send_dingtalk(url, title, content, image_url=None, action_url=None):
    """
    发送钉钉消息，优先使用 Markdown 格式
    """
    # 构造 Markdown 内容
    markdown_text = f"# {title}\n\n"
    
    # 如果有图片，放在最前面
    if image_url:
        markdown_text += f"![封面]({image_url})\n\n"
        
    markdown_text += content
    
    if action_url:
        markdown_text += f"\n\n[查看详情]({action_url})"

    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": markdown_text
        }
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        resp_json = response.json()
        if response.status_code == 200 and resp_json.get('errcode') == 0:
            print(f"✅ 钉钉推送成功")
        else:
            print(f"⚠️ 钉钉推送失败: {response.text}")
    except Exception as e:
        print(f"❌ 钉钉请求异常: {e}")
