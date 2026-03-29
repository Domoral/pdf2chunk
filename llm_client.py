import os
import json
import re
import base64
from pathlib import Path
from typing import List, Dict, Any
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


def recognizer(input_image: str, output_text_file: str) -> None:
    """
    识别图片中的数学题目，将结果保存到文本文件。

    Args:
        input_image: 输入图片路径
        output_text_file: 输出文本文件路径
    """
    client = LLMClient()
    prompt = prompt_templates["ocr_recognizer"]

    result = client._call_vision_model(input_image, prompt)

    Path(output_text_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_text_file, "w", encoding="utf-8") as f:
        f.write(result)


def parse_questions(text: str) -> List[str]:
    """
    从OCR输出文本中解析出各个题目。

    Args:
        text: OCR输出的文本

    Returns:
        题目列表
    """
    pattern = r'question:\s*(.*?)\s*:noitseuq'
    matches = re.findall(pattern, text, re.DOTALL)
    return [q.strip() for q in matches if q.strip()]


def slicer(input_text_file: str, output_text_folder: str) -> None:
    """
    将OCR输出的文本分割成独立的题目文件。

    Args:
        input_text_file: OCR输出的文本文件路径
        output_text_folder: 输出题目文件夹路径
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


def parse_annotation(response: str) -> Dict[str, Any]:
    """
    从LLM响应中解析JSON标注结果。

    Args:
        response: LLM的响应文本

    Returns:
        解析后的字典
    """
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        raise


def annotator(input_text_folder: str, output_json_folder: str) -> None:
    """
    对题目进行自动标注，输出JSON文件。

    Args:
        input_text_folder: 输入题目文件夹路径
        output_json_folder: 输出JSON文件夹路径
    """
    client = LLMClient()
    template = prompt_templates["question_annotator"]

    input_path = Path(input_text_folder)
    output_path = Path(output_json_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    question_files = sorted(input_path.glob("question_*.txt"))

    for question_file in question_files:
        with open(question_file, "r", encoding="utf-8") as f:
            question_content = f.read().strip()

        prompt = template.format(question_content=question_content)
        response = client._call_text_model(prompt)

        annotation = parse_annotation(response)

        result = {
            "content": question_content,
            "difficulty": annotation.get("difficulty", ""),
            "question_type": annotation.get("question_type", ""),
            "knowledge_points": annotation.get("knowledge_points", [])
        }

        output_file = output_path / question_file.name.replace(".txt", ".json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)


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
        recognizer(sys.argv[2], sys.argv[3])
    elif command == "slicer" and len(sys.argv) == 4:
        slicer(sys.argv[2], sys.argv[3])
    elif command == "annotator" and len(sys.argv) == 4:
        annotator(sys.argv[2], sys.argv[3])
    else:
        print("Invalid command or arguments")
        sys.exit(1)
