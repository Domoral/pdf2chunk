import os
from pathlib import Path
from typing import List
from pdf2image import convert_from_path


def pdf_to_images(input_pdf: str, output_folder: str, dpi: int = 300, fmt: str = "png") -> List[str]:
    """
    将PDF按页转换为图片。

    Args:
        input_pdf: 输入PDF文件路径
        output_folder: 输出图片文件夹路径
        dpi: 图片分辨率，默认300
        fmt: 图片格式，默认png

    Returns:
        生成的图片路径列表
    """
    pdf_path = Path(input_pdf)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"正在转换PDF: {pdf_path.name}")
    images = convert_from_path(input_pdf, dpi=dpi)

    image_paths = []
    for i, image in enumerate(images, 1):
        output_file = output_path / f"page_{i:04d}.{fmt}"
        image.save(output_file, fmt.upper())
        image_paths.append(str(output_file))
        print(f"  已保存: {output_file.name}")

    print(f"共转换 {len(images)} 页")
    return image_paths


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python pdf_to_images.py <input_pdf> <output_folder> [dpi] [fmt]")
        print("Example: python pdf_to_images.py input.pdf output_images 300 png")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_folder = sys.argv[2]
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    fmt = sys.argv[4] if len(sys.argv) > 4 else "png"

    pdf_to_images(input_pdf, output_folder, dpi, fmt)
