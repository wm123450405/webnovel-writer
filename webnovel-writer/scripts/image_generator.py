"""
图片生成辅助模块

支持通过环境变量配置图片生成服务：
- IMAGE_GEN_PROVIDER: 服务提供商 (openai/anthropic/custom)
- IMAGE_GEN_API_KEY: API密钥
- IMAGE_GEN_MODEL: 模型名称
- IMAGE_GEN_BASE_URL: API地址

使用示例：
    from image_generator import generate_image

    # 生成图片
    image_bytes = generate_image("一个穿蓝色长袍的少女", "1024x1024")
    with open("output.png", "wb") as f:
        f.write(image_bytes)
"""

import os
import io
import base64
import requests
from typing import Optional


def get_config() -> dict:
    """获取图片生成配置"""
    return {
        "provider": os.environ.get("IMAGE_GEN_PROVIDER", "openai"),
        "api_key": os.environ.get("IMAGE_GEN_API_KEY", ""),
        "model": os.environ.get("IMAGE_GEN_MODEL", "dall-e-3"),
        "base_url": os.environ.get("IMAGE_GEN_BASE_URL", "https://api.openai.com/v1"),
    }


def generate_image(prompt: str, size: str = "1024x1024", quality: str = "standard") -> bytes:
    """
    调用图片生成服务生成图片

    Args:
        prompt: 图片描述提示词
        size: 图片尺寸 (如 "1024x1024", "1536x1536")
        quality: 图片质量 ("standard" 或 "hd")

    Returns:
        图片二进制数据

    Raises:
        Exception: 如果未配置 API 密钥或生成失败
    """
    config = get_config()
    provider = config["provider"]
    api_key = config["api_key"]
    model = config["model"]
    base_url = config["base_url"]

    if not api_key:
        raise Exception("未配置 IMAGE_GEN_API_KEY 环境变量，请设置图片生成服务的 API 密钥")

    if provider == "openai":
        return _generate_openai(prompt, size, quality, api_key, model, base_url)
    elif provider == "anthropic":
        return _generate_anthropic(prompt, size, api_key, model)
    else:
        raise Exception(f"不支持的图片生成服务商: {provider}")


def _generate_openai(prompt: str, size: str, quality: str, api_key: str, model: str, base_url: str) -> bytes:
    """调用 OpenAI API 生成图片"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 映射模型到支持的尺寸
    size_map = {
        "1024x1024": "1024x1024",
        "1536x1536": "1024x1024",  # OpenAI 不支持 1536，使用 1024
        "512x512": "512x512",
    }
    actual_size = size_map.get(size, "1024x1024")

    data = {
        "model": model,
        "prompt": prompt,
        "size": actual_size,
        "quality": quality,
        "n": 1
    }

    response = requests.post(
        f"{base_url}/images/generations",
        headers=headers,
        json=data,
        timeout=120
    )

    if response.status_code == 200:
        result = response.json()
        image_url = result["data"][0]["url"]
        # 下载图片
        img_response = requests.get(image_url)
        return img_response.content
    else:
        raise Exception(f"OpenAI 图片生成失败: {response.status_code} - {response.text}")


def _generate_anthropic(prompt: str, size: str, api_key: str, model: str) -> bytes:
    """
    调用 Anthropic API 生成图片
    注意: Anthropic 目前不支持图片生成，此函数作为占位符
    """
    # Anthropic 目前不支持图片生成，抛出异常
    raise Exception("Anthropic API 目前不支持图片生成，请使用 OpenAI 或其他服务商")


def generate_and_save(prompt: str, output_path: str, size: str = "1024x1024") -> str:
    """
    生成图片并保存到文件

    Args:
        prompt: 图片描述提示词
        output_path: 输出文件路径
        size: 图片尺寸

    Returns:
        保存的文件路径
    """
    image_bytes = generate_image(prompt, size)
    with open(output_path, "wb") as f:
        f.write(image_bytes)
    return output_path


if __name__ == "__main__":
    # 测试用
    import sys
    if len(sys.argv) < 3:
        print("用法: python image_generator.py <prompt> <output_path> [size]")
        sys.exit(1)

    prompt = sys.argv[1]
    output_path = sys.argv[2]
    size = sys.argv[3] if len(sys.argv) > 3 else "1024x1024"

    try:
        path = generate_and_save(prompt, output_path, size)
        print(f"图片已保存到: {path}")
    except Exception as e:
        print(f"生成失败: {e}")
        sys.exit(1)
