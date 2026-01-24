import apprise
from apprise import NotifyFormat
import os
import sys
import json
try:
    from dotenv import load_dotenv
    # 智能加载 .env
    # 1. 确定路径
    utils_dir = os.path.dirname(os.path.abspath(__file__))
    sub_project_dir = os.path.dirname(utils_dir)       # e.g., DailyNewsBot
    root_project_dir = os.path.dirname(sub_project_dir) # e.g., MyAutomationTools
    
    # 2. 依次尝试加载（load_dotenv 默认不覆盖已存在的变量，所以先加载的优先级高）
    # 优先加载子项目目录下的 .env (如果有特定配置)
    load_dotenv(os.path.join(sub_project_dir, '.env'))
    # 其次加载根目录下的 .env (通用配置)
    load_dotenv(os.path.join(root_project_dir, '.env'))
except ImportError:
    pass

def send(title, content):
    """
    统一消息推送函数
    从环境变量 NOTIFIER_URL 读取配置
    支持多个服务，用逗号分隔
    """
    notifier_url = os.environ.get("NOTIFIER_URL")
    
    if not notifier_url:
        print("⚠️ 未配置 NOTIFIER_URL，仅打印日志。")
        print(f"[{title}] {content}")
        return

    # 智能识别钉钉：无论是 Apprise 格式还是原始 HTTPS Webhook
    if "dingtalk://" in notifier_url or "oapi.dingtalk.com" in notifier_url:
        # 终极方案：手动 requests 发送
        try:
            token = ""
            if "dingtalk://" in notifier_url:
                # 提取 token (Apprise 格式)
                token = notifier_url.split("dingtalk://")[1].split("/")[0].split("?")[0]
            elif "access_token=" in notifier_url:
                # 提取 token (HTTPS 格式)
                token = notifier_url.split("access_token=")[1].split("&")[0]
            
            if token:
                api_url = f"https://oapi.dingtalk.com/robot/send?access_token={token}"
                
                headers = {'Content-Type': 'application/json'}
                # 钉钉安全设置关键字拦截修复：
                # 如果机器人设置了“自定义关键字”，内容中必须包含该关键字。
                # 这里可以尝试把 title 也拼接到 text 里，或者在 title 前面加个通用前缀
                # 假设关键字可能包含 "通知"、"监控"、"日报" 等
                # 最稳妥的方式是将 title 拼接到 text 的第一行，因为 Markdown 的 title 字段仅在通知栏展示
                
                final_text = f"# {title}\n\n{content}"
                
                data = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": title,
                        "text": final_text
                    }
                }
                
                import requests
                response = requests.post(api_url, headers=headers, data=json.dumps(data), timeout=30)
                if response.status_code == 200 and response.json().get('errcode') == 0:
                    print(f"✅ [原生请求] 钉钉 Markdown 推送成功: {title}")
                    return # 成功后直接返回，不再走 Apprise
                else:
                    print(f"⚠️ [原生请求] 钉钉推送失败: {response.text}")
        except Exception as e:
            print(f"⚠️ [原生请求] 异常: {e}")
            # 如果原生失败，继续尝试 Apprise
    
    # 特殊处理：如果检测到是钉钉且 Apprise 无法发送 Markdown，回退到 requests 原生发送
    # 这是最保险的方案
    # if "dingtalk://" in notifier_url and "requests" not in sys.modules:
    #     import requests
    
    # 支持多个 URL，用逗号或空格分隔
    urls = notifier_url.split(',')
    
    # 临时补丁：如果 Apprise 真的不行，我们直接拦截钉钉请求
    # 但为了保持架构统一，我们还是先试 Apprise
    apobj = apprise.Apprise()
    for url in urls:
        if url.strip():
            apobj.add(url.strip())
    
    try:
        # Apprise 会自动处理不同服务的格式
        # 终极方案：手动构造 Markdown 类型的 Apprise 调用
        # DingTalk 插件如果配置了 ?msgtype=markdown 会优先使用
        apobj.notify(
            body=content,
            title=title,
            body_format=NotifyFormat.MARKDOWN
        )
        print(f"✅ 消息已通过 Apprise 推送: {title}")
    except Exception as e:
        print(f"❌ 推送失败: {e}")
