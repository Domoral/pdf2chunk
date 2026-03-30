import os
import sys
from pathlib import Path
from llm_client import recognizer_batch, slicer, annotator_batch


def process_images(images_dir: str, output_dir: str = "output", batch_size: int = 5) -> None:
    """
    从已有图片开始的处理流程：图片 -> OCR -> 分割 -> 标注 -> JSON

    Args:
        images_dir: 输入图片文件夹路径
        output_dir: 输出根目录
        batch_size: 并行处理的批次大小，默认5
    """
    images_path = Path(images_dir)
    base_dir = Path(output_dir)

    # 定义中间文件夹
    ocr_dir = base_dir / "ocr_text"
    all_questions_dir = base_dir / "all_questions"
    json_dir = base_dir / "json_output"

    print("=" * 60)
    print(f"开始处理图片: {images_dir}")
    print("=" * 60)

    # 获取所有图片文件
    image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
    image_paths = sorted([
        p for p in images_path.iterdir()
        if p.is_file() and p.suffix.lower() in image_extensions
    ])

    if not image_paths:
        print(f"错误: 在 {images_dir} 中没有找到图片文件")
        sys.exit(1)

    print(f"共找到 {len(image_paths)} 张图片")

    # 步骤1: OCR识别（批量并行）
    print(f"\n[步骤1] OCR识别 (并行{batch_size}个)...")
    ocr_dir.mkdir(parents=True, exist_ok=True)
    
    image_path_list = [str(p) for p in image_paths]
    ocr_file_list = [str(ocr_dir / f"{p.stem}.txt") for p in image_paths]
    
    recognizer_batch(image_path_list, ocr_file_list, max_workers=batch_size)

    # 步骤2: 分割题目
    print("\n[步骤2] 分割题目...")
    all_questions_dir.mkdir(parents=True, exist_ok=True)

    question_counter = 0
    for ocr_file in sorted(ocr_dir.glob("*.txt")):
        print(f"  处理 {ocr_file.name}...")
        temp_dir = base_dir / "temp_split"
        count = slicer(str(ocr_file), str(temp_dir))

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

    # 步骤3: 自动标注（批量并行）
    print(f"\n[步骤3] 自动标注 (并行{batch_size}个)...")
    annotator_batch(str(all_questions_dir), str(json_dir), max_workers=batch_size)

    print("\n" + "=" * 60)
    print("处理完成!")
    print(f"输出目录: {base_dir}")
    print(f"  - OCR文本: {ocr_dir}")
    print(f"  - 分割后题目: {all_questions_dir}")
    print(f"  - 有效题目JSON: {json_dir}")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main_from_images.py <images_dir> [output_dir] [batch_size]")
        print("Example: python main_from_images.py images/ output 5")
        sys.exit(1)

    images_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    if not os.path.exists(images_dir):
        print(f"错误: 文件夹不存在 {images_dir}")
        sys.exit(1)

    process_images(images_dir, output_dir, batch_size)
