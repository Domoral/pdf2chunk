import os
import json
import re
import base64
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI

from prompt_templates import prompt_templates

load_dotenv()


class LLMClient:
    def __init__(self):
        self.zhipu_client = OpenAI(
            api_key=os.getenv("ZHIPUAI_API_KEY"),
            base_url="https://open.bigmodel.cn/api/paas/v4"
        )
        self.deepseek_client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        self.glm_model = os.getenv("GLM_MODEL", "glm-4v-flash")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _call_vision_model(self, image_path: str, prompt: str) -> str:
        base64_image = self._encode_image(image_path)
        response = self.zhipu_client.chat.completions.create(
            model=self.glm_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        )
        return response.choices[0].message.content

    def _call_text_model(self, prompt: str) -> str:
        response = self.deepseek_client.chat.completions.create(
            model=self.deepseek_model,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content


def _recognize_single(args: tuple) -> tuple:
    """单个图片识别的辅助函数"""
    image_path, output_text_file, prompt = args
    try:
        client = LLMClient()
        result = client._call_vision_model(image_path, prompt)
        Path(output_text_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_text_file, "w", encoding="utf-8") as f:
            f.write(result)
        return (image_path, True, None)
    except Exception as e:
        return (image_path, False, str(e))


def recognizer_batch(image_paths: List[str], output_text_files: List[str], max_workers: int = 5) -> None:
    """
    批量识别图片中的数学题目，并行处理。

    Args:
        image_paths: 输入图片路径列表
        output_text_files: 输出文本文件路径列表
        max_workers: 并行线程数，默认5
    """
    prompt = prompt_templates["ocr_recognizer"]
    args_list = list(zip(image_paths, output_text_files, [prompt] * len(image_paths)))

    completed = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_recognize_single, args): args for args in args_list}
        for future in as_completed(futures):
            image_path, success, error = future.result()
            if success:
                completed += 1
                print(f"  完成: {Path(image_path).name}")
            else:
                failed += 1
                print(f"  失败: {Path(image_path).name} - {error}")

    print(f"  OCR完成: {completed} 成功, {failed} 失败")


def parse_questions(text: str) -> List[str]:
    """
    从OCR输出文本中解析出各个题目。
    每道题以 "question:" 开头，到下一题的 "question:" 或文本结束为止。

    Args:
        text: OCR输出的文本

    Returns:
        题目列表
    """
    parts = re.split(r'question:\s*', text, flags=re.IGNORECASE)
    questions = []
    for part in parts:
        part = part.strip()
        if part:
            part = re.sub(r'\s*:noitseuq\s*$', '', part, flags=re.IGNORECASE)
            questions.append(part)
    return questions


def slicer(input_text_file: str, output_text_folder: str) -> int:
    """
    将OCR输出的文本分割成独立的题目文件。

    Args:
        input_text_file: OCR输出的文本文件路径
        output_text_folder: 输出题目文件夹路径

    Returns:
        提取的题目数量
    """
    with open(input_text_file, "r", encoding="utf-8") as f:
        content = f.read()

    questions = parse_questions(content)

    output_path = Path(output_text_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    for i, question in enumerate(questions, 1):
        output_file = output_path / f"question_{i:04d}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(question)

    return len(questions)


def parse_annotation(response: str) -> Dict[str, Any]:
    """
    从LLM响应中解析JSON标注结果。

    Args:
        response: LLM的响应文本

    Returns:
        解析后的字典
    """
    # 尝试匹配 ```json ... ``` 代码块
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # 尝试匹配 ``` ... ``` 代码块
    json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # 尝试从整个响应中提取 JSON 对象
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass

    # 使用正则匹配最外层的大括号
    json_match = re.search(r'\{[\s\S]*?"valid"[\s\S]*?\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # 如果都失败了，尝试贪婪匹配
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # 如果都失败了，返回一个包含原始响应的字典，让调用者处理
    return {"_parse_error": True, "_raw_response": response}


def _annotate_single(args: tuple) -> tuple:
    """单个题目标注的辅助函数"""
    question_file, output_file, template = args
    try:
        with open(question_file, "r", encoding="utf-8") as f:
            question_content = f.read().strip()

        client = LLMClient()
        prompt = template.replace("{question_content}", question_content)
        response = client._call_text_model(prompt)
        annotation = parse_annotation(response)

        # 检查是否解析失败
        if annotation.get("_parse_error"):
            raw = annotation.get("_raw_response", "")[:100]
            return (question_file.name, "error", f"JSON解析失败: {raw}")

        if not annotation.get("valid", True):
            return (question_file.name, "invalid", None)

        result = {
            "content": question_content,
            "difficulty": annotation.get("difficulty", ""),
            "question_type": annotation.get("question_type", ""),
            "knowledge_points": annotation.get("knowledge_points", [])
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return (question_file.name, "valid", None)
    except Exception as e:
        return (question_file.name, "error", str(e))


def annotator_batch(input_text_folder: str, output_json_folder: str, max_workers: int = 16) -> None:
    """
    对题目进行自动标注，并行处理。无效题目直接丢弃。

    Args:
        input_text_folder: 输入题目文件夹路径
        output_json_folder: 输出JSON文件夹路径
        max_workers: 并行线程数，默认5
    """
    template = prompt_templates["question_annotator"]

    input_path = Path(input_text_folder)
    output_path = Path(output_json_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    question_files = sorted(input_path.glob("question_*.txt"))

    args_list = [
        (q_file, output_path / q_file.name.replace(".txt", ".json"), template)
        for q_file in question_files
    ]

    valid_count = 0
    invalid_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_annotate_single, args): args for args in args_list}
        for future in as_completed(futures):
            name, status, error = future.result()
            if status == "valid":
                valid_count += 1
                print(f"  完成: {name}")
            elif status == "invalid":
                invalid_count += 1
                print(f"  跳过无效: {name}")
            else:
                error_count += 1
                print(f"  错误: {name} - {error}")

    print(f"  标注完成: {valid_count} 有效, {invalid_count} 无效, {error_count} 错误")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python llm_client.py <command> [args...]")
        print("Commands:")
        print("  recognizer <input_image> <output_text_file>")
        print("  slicer <input_text_file> <output_text_folder>")
        print("  annotator <input_text_folder> <output_json_folder>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "recognizer" and len(sys.argv) == 4:
        from llm_client import recognizer_batch
        recognizer_batch([sys.argv[2]], [sys.argv[3]])
    elif command == "slicer" and len(sys.argv) == 4:
        slicer(sys.argv[2], sys.argv[3])
    elif command == "annotator" and len(sys.argv) == 4:
        annotator_batch(sys.argv[2], sys.argv[3])
    else:
        print("Invalid command or arguments")
        sys.exit(1)
