import os
import sys
from pathlib import Path
from pdf_to_images import pdf_to_images
from llm_client import recognizer, slicer, annotator


def process_pdf(input_pdf: str, output_dir: str = "output") -> None:
    """
    完整的PDF处理流程：PDF -> 图片 -> OCR -> 分割 -> 标注 -> JSON

    Args:
        input_pdf: 输入PDF文件路径
        output_dir: 输出根目录
    """
    pdf_name = Path(input_pdf).stem
    base_dir = Path(output_dir) / pdf_name

    # 定义中间文件夹
    images_dir = base_dir / "images"
    ocr_dir = base_dir / "ocr_text"
    questions_dir = base_dir / "questions"
    json_dir = base_dir / "json_output"

    print("=" * 60)
    print(f"开始处理PDF: {input_pdf}")
    print("=" * 60)

    # 步骤1: PDF转图片
    print("\n[步骤1] PDF转换为图片...")
    image_paths = pdf_to_images(input_pdf, str(images_dir), dpi=300, fmt="png")

    # 步骤2: OCR识别
    print("\n[步骤2] OCR识别...")
    ocr_dir.mkdir(parents=True, exist_ok=True)
    for image_path in image_paths:
        page_name = Path(image_path).stem
        ocr_file = ocr_dir / f"{page_name}.txt"
        print(f"  识别 {page_name}...")
        recognizer(image_path, str(ocr_file))

    # 步骤3: 分割题目
    print("\n[步骤3] 分割题目...")
    all_questions_dir = base_dir / "all_questions"
    all_questions_dir.mkdir(parents=True, exist_ok=True)

    question_counter = 0
    for ocr_file in sorted(ocr_dir.glob("page_*.txt")):
        print(f"  处理 {ocr_file.name}...")
        temp_dir = base_dir / "temp_split"
        slicer(str(ocr_file), str(temp_dir))

        # 将分割后的题目移到统一目录，重新编号
        for q_file in sorted(temp_dir.glob("question_*.txt")):
            question_counter += 1
            new_name = all_questions_dir / f"question_{question_counter:04d}.txt"
            q_file.rename(new_name)

        # 清理临时目录
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)

    print(f"  共提取 {question_counter} 道题目")

    # 步骤4: 自动标注
    print("\n[步骤4] 自动标注...")
    annotator(str(all_questions_dir), str(json_dir))

    print("\n" + "=" * 60)
    print("处理完成!")
    print(f"输出目录: {base_dir}")
    print(f"  - 图片: {images_dir}")
    print(f"  - OCR文本: {ocr_dir}")
    print(f"  - 分割后题目: {all_questions_dir}")
    print(f"  - 最终JSON: {json_dir}")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <input_pdf> [output_dir]")
        print("Example: python main.py input.pdf output")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"

    if not os.path.exists(input_pdf):
        print(f"错误: 文件不存在 {input_pdf}")
        sys.exit(1)

    process_pdf(input_pdf, output_dir)
