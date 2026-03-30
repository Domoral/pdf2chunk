import os
import sys
from pathlib import Path
from llm_client import annotator_batch


def annotate_questions(questions_dir: str, output_dir: str = "output", batch_size: int = 16) -> None:
    """
    仅执行标注步骤：题目 -> 标注 -> JSON

    Args:
        questions_dir: 输入题目文件夹路径（包含 question_*.txt 文件）
        output_dir: 输出根目录
        batch_size: 并行处理的批次大小，默认16
    """
    questions_path = Path(questions_dir)
    base_dir = Path(output_dir)
    json_dir = base_dir / "json_output"

    print("=" * 60)
    print(f"开始标注题目: {questions_dir}")
    print("=" * 60)

    # 检查输入文件夹
    if not questions_path.exists():
        print(f"错误: 文件夹不存在 {questions_dir}")
        sys.exit(1)

    question_files = list(questions_path.glob("question_*.txt"))
    if not question_files:
        print(f"错误: 在 {questions_dir} 中没有找到 question_*.txt 文件")
        sys.exit(1)

    print(f"共找到 {len(question_files)} 道题目")

    # 执行自动标注（批量并行）
    print(f"\n[标注] 自动标注 (并行{batch_size}个)...")
    annotator_batch(str(questions_path), str(json_dir), max_workers=batch_size)

    print("\n" + "=" * 60)
    print("处理完成!")
    print(f"输出目录: {base_dir}")
    print(f"  - 有效题目JSON: {json_dir}")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main_annotate_only.py <questions_dir> [output_dir] [batch_size]")
        print("Example: python main_annotate_only.py all_questions/ output 5")
        sys.exit(1)

    questions_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 16

    annotate_questions(questions_dir, output_dir, batch_size)
