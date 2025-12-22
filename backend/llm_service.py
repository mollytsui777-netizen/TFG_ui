from openai import OpenAI
import os
import json

# === API 配置文件路径 ===
CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'api_config.json')
EXAMPLE_CONFIG_FILE = os.path.join(CONFIG_DIR, 'api_config.example.json')

def load_api_config():
    """
    从配置文件加载API配置
    优先级：环境变量 > 配置文件 > 默认值
    """
    config = {}
    
    # 如果配置文件存在，读取配置
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"[LLM Service] 已加载配置文件: {CONFIG_FILE}")
        except Exception as e:
            print(f"[LLM Service] 读取配置文件失败: {e}，使用默认配置")
            config = {}
    else:
        print(f"[LLM Service] 配置文件不存在: {CONFIG_FILE}")
        # 确保config目录存在
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(EXAMPLE_CONFIG_FILE):
            print(f"[LLM Service] 请复制 {EXAMPLE_CONFIG_FILE} 为 {CONFIG_FILE} 并填入你的API密钥")
    
    # 环境变量优先级更高，覆盖配置文件中的值
    api_config = {}
    for key in ["openai", "zhipu", "deepseek"]:
        api_config[key] = {
            "api_key": os.getenv(
                f"{key.upper()}_API_KEY",
                config.get(key, {}).get("api_key", "sk-xxxxxxxx")
            ),
            "base_url": config.get(key, {}).get("base_url", ""),
            "model": config.get(key, {}).get("model", ""),
            "enabled": config.get(key, {}).get("enabled", True)
        }
    
    # 设置默认值（如果配置文件中没有）
    if not api_config["openai"]["base_url"]:
        api_config["openai"]["base_url"] = "https://api.openai.com/v1"
        api_config["openai"]["model"] = "gpt-3.5-turbo"
    
    if not api_config["zhipu"]["base_url"]:
        api_config["zhipu"]["base_url"] = "https://open.bigmodel.cn/api/paas/v4/"
        api_config["zhipu"]["model"] = "glm-4"
    
    if not api_config["deepseek"]["base_url"]:
        api_config["deepseek"]["base_url"] = "https://api.deepseek.com"
        api_config["deepseek"]["model"] = "deepseek-chat"
    
    return api_config

# 加载API配置
API_CONFIG = load_api_config()

def query_llm(text, api_choice="zhipu"):
    """
    统一的 LLM 调用接口
    """
    print(f"[LLM Service] 正在调用: {api_choice}")
    
    # 重新加载配置（支持动态更新）
    global API_CONFIG
    API_CONFIG = load_api_config()
    
    config = API_CONFIG.get(api_choice)
    if not config:
        print(f"[LLM Service] 未找到 {api_choice} 配置，回退到 zhipu")
        api_choice = "zhipu"
        config = API_CONFIG.get("zhipu")
    
    # 检查API是否启用
    if not config.get("enabled", True):
        print(f"[LLM Service] {api_choice} API未启用，尝试使用其他可用API")
        # 按优先级顺序尝试：deepseek > openai > zhipu
        fallback_order = ["deepseek", "openai", "zhipu"]
        for key in fallback_order:
            if key == api_choice:
                continue
            cfg = API_CONFIG.get(key)
            if cfg and cfg.get("enabled", True):
                # 检查密钥是否有效
                api_key = cfg.get("api_key", "")
                default_keys = ["sk-xxxxxxxx", "your-zhipu-api-key-here", "sk-your-deepseek-api-key-here"]
                if api_key and api_key not in default_keys:
                    print(f"[LLM Service] 切换到: {key}")
                    config = cfg
                    api_choice = key
                    break
    
    # 检查API密钥是否有效（排除默认占位符）
    default_keys = ["sk-xxxxxxxx", "your-zhipu-api-key-here", "sk-your-deepseek-api-key-here"]
    api_key = config.get("api_key", "")
    if not api_key or api_key in default_keys:
        print(f"[LLM Service] 警告: {api_choice} 的API密钥未配置或使用默认值")
        return "抱歉，API密钥未配置，请检查配置文件 backend/config/api_config.json 或环境变量。"

    try:
        # 使用 OpenAI SDK 统一调用 (智谱、DeepSeek 等现在都兼容此格式)
        client = OpenAI(
            api_key=config['api_key'],
            base_url=config['base_url']
        )

        response = client.chat.completions.create(
            model=config['model'],
            messages=[
                {"role": "system", "content": "你是一个数字人助手，请用简短、口语化的中文回答用户，字数控制在50字以内。"},
                {"role": "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        reply = response.choices[0].message.content
        print(f"[LLM Service] 回复: {reply}")
        return reply

    except Exception as e:
        print(f"[LLM Service] 调用失败: {e}")
        return "抱歉，我现在连接大脑有点问题，请稍后再试。"