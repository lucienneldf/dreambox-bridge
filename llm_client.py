"""
LLM API 调用模块
支持多个 LLM 提供商：DeepSeek、豆包、Kimi、通义千问、自定义
"""
import requests
import json
import os
from typing import Dict, List, Optional


# LLM 提供商配置
LLM_PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat"
    },
    "doubao": {
        "name": "豆包（字节跳动）",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "models": ["doubao-pro-4k", "doubao-pro-32k", "doubao-lite-4k"],
        "default_model": "doubao-pro-4k"
    },
    "kimi": {
        "name": "Kimi（月之暗面）",
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "default_model": "moonshot-v1-8k"
    },
    "qwen": {
        "name": "通义千问（阿里）",
        "base_url": "https://dashscope.aliyuncs.com/api/v1",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max"],
        "default_model": "qwen-turbo"
    },
    "glm": {
        "name": "智谱 AI（GLM）",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-flash", "glm-4", "glm-4-plus"],
        "default_model": "glm-4-flash"
    },
    "custom": {
        "name": "自定义",
        "base_url": "",
        "models": [],
        "default_model": ""
    }
}


class LLMClient:
    """LLM API 客户端"""
    
    def __init__(self, config_path: str = "data/config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_config(self, config: Dict):
        """保存配置"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def get_llm_config(self) -> Dict:
        """获取 LLM 配置"""
        return self.config.get("llm_api", {})
    
    def set_llm_config(self, provider: str, api_key: str, 
                       base_url: str = None, model: str = None):
        """设置 LLM 配置"""
        if "llm_api" not in self.config:
            self.config["llm_api"] = {}
        
        self.config["llm_api"]["provider"] = provider
        self.config["llm_api"]["api_key"] = api_key
        
        # 如果是自定义，使用用户提供的 base_url
        if provider == "custom" and base_url:
            self.config["llm_api"]["base_url"] = base_url
        elif provider in LLM_PROVIDERS:
            self.config["llm_api"]["base_url"] = LLM_PROVIDERS[provider]["base_url"]
        
        # 设置模型
        if model:
            self.config["llm_api"]["model"] = model
        elif provider in LLM_PROVIDERS:
            self.config["llm_api"]["model"] = LLM_PROVIDERS[provider]["default_model"]
        
        self._save_config(self.config)
    
    def test_connection(self) -> Dict:
        """测试 API 连接"""
        llm_config = self.get_llm_config()
        if not llm_config.get("api_key"):
            return {"success": False, "message": "未配置 API Key"}
        
        try:
            # 发送简单测试请求
            response = self._call_api("你好，请回复'连接成功'")
            if response:
                return {"success": True, "message": f"连接成功！模型回复：{response[:50]}..."}
            else:
                return {"success": False, "message": "API 调用失败"}
        except Exception as e:
            return {"success": False, "message": f"连接失败：{str(e)}"}
    
    def _call_api(self, prompt: str, system_prompt: str = None, 
                  temperature: float = 0.7) -> str:
        """调用 LLM API"""
        llm_config = self.get_llm_config()
        
        if not llm_config.get("api_key"):
            raise Exception("未配置 API Key，请先在设置页面配置")
        
        provider = llm_config.get("provider", "deepseek")
        base_url = llm_config.get("base_url", LLM_PROVIDERS.get(provider, {}).get("base_url", ""))
        api_key = llm_config.get("api_key", "")
        model = llm_config.get("model", LLM_PROVIDERS.get(provider, {}).get("default_model", ""))
        
        if not base_url:
            raise Exception(f"未配置 API Base URL")
        
        # 构建请求
        url = f"{base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4000
        }
        
        # 发送请求
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"API 调用失败：{response.status_code} - {response.text}")
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def grade_material(self, material_text: str, skill_content: str) -> str:
        """素材筛选（使用 Skill 1）"""
        system_prompt = f"""你是梦想盒子素材筛选助手。
请严格按照以下规则进行筛选：

{skill_content}
"""
        
        prompt = f"""请对以下素材进行质量判定和分级：

{material_text}

请按照固定格式输出：
【质量等级】S1/S2/S3/S4/S2-
【判定依据（五段式）】...
【注意点】...
"""
        
        return self._call_api(prompt, system_prompt, temperature=0.3)
    
    def generate_copy(self, material_text: str, grade_result: str, 
                      skill_content: str) -> str:
        """文案生成（使用 Skill 2）"""
        system_prompt = f"""你是梦想盒子文案生成助手。
请严格按照以下规则生成文案：

{skill_content}
"""
        
        prompt = f"""请根据以下素材和筛选结果，生成一篇公募反馈文案：

【素材原文】
{material_text}

【筛选结果】
{grade_result}

请按照固定格式输出：
【标题】...
【摘要】...
【正文】...
【感谢语】...
【成稿说明】...
"""
        
        return self._call_api(prompt, system_prompt, temperature=0.7)


# 全局实例
llm_client = LLMClient()


def get_providers() -> Dict:
    """获取所有支持的提供商"""
    return LLM_PROVIDERS


def get_provider_models(provider: str) -> List[str]:
    """获取指定提供商的模型列表"""
    if provider in LLM_PROVIDERS:
        return LLM_PROVIDERS[provider]["models"]
    return []
