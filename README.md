# pdf2chunk

RAG数据库构建的前置项目——将扫描件PDF转化为结构化题目数据。

## 项目概述

本项目用于将扫描版PDF数学题库（每页包含多个题目）预处理为文本格式，并将每道题目分割为独立的chunk，包含题目内容、难度、题型和知识点标注，便于后续的embedding和存储。

## 功能特性

- **PDF转图片**：将PDF逐页转换为高清图片
- **OCR识别**：提取文本并将数学公式转换为LaTeX格式
- **题目分割**：自动识别题目边界，将多题目页面分割为单题
- **智能标注**：使用LLM自动标注难度、题型和知识点
- **并行处理**：支持多线程并行加速处理
- **无效题目过滤**：自动识别并丢弃残题、带图片的题目

## 项目结构

```
pdf2chunk/
├── main.py                    # 完整流程：PDF → JSON
├── main_from_images.py        # 从已有图片开始处理
├── main_annotate_only.py      # 仅执行标注步骤
├── pdf_to_images.py           # PDF转图片工具
├── llm_client.py              # LLM客户端（OCR + 标注）
├── prompt_templates.py        # Prompt模板
├── requirements.txt           # 依赖列表
├── .env                       # API密钥配置（需自行创建）
└── output/                    # 输出目录
    ├── images/                # PDF转换的图片
    ├── ocr_text/              # OCR识别结果
    ├── all_questions/         # 分割后的单题文件
    └── json_output/           # 最终JSON输出
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置API密钥

创建 `.env` 文件，配置以下环境变量：

```env
# OCR模型配置（视觉模型）
OCR_BASE_URL=your_ocr_url
OCR_API_KEY=your_ocr_api_key
OCR_MODEL=your_ocr_model

# 标注模型配置（文本模型）
ANNOTATION_BASE_URL=your_llm_url
ANNOTATION_API_KEY=your_annotation_api_key
ANNOTATION_MODEL=your_reasoner_model
```

## 使用方法

### 1. 完整流程（PDF → JSON）

```bash
python main.py <input_pdf> [output_dir] [batch_size]
```

示例：
```bash
python main.py 数学题库.pdf output 5
```

### 2. 从已有图片开始

如果已经有PDF转换好的图片，跳过PDF转换步骤：

```bash
python main_from_images.py <images_dir> [output_dir] [batch_size]
```

示例：
```bash
python main_from_images.py images/ output 5
```

### 3. 仅执行标注

如果已经有分割好的题目文件，只执行标注步骤：

```bash
python main_annotate_only.py <questions_dir> [output_dir] [batch_size]
```

示例：
```bash
python main_annotate_only.py all_questions/ output 16
```

## 输出格式

每个有效的题目会生成一个JSON文件，格式如下：

```json
{
  "content": "题目内容，包含LaTeX格式的数学公式",
  "difficulty": "简单|中等|困难",
  "question_type": "单选题|多选题|填空题|计算题|证明题|应用题",
  "knowledge_points": ["知识点1", "知识点2", ...]
}
```

## 处理流程

```
PDF → 图片 → OCR识别 → 题目分割 → 自动标注 → JSON
```

1. **PDF转图片**：使用pdf2image将PDF转换为PNG图片
2. **OCR识别**：调用视觉模型识别图片中的文字和数学公式，转换为LaTeX
3. **题目分割**：使用正则表达式识别题目编号，将多题目页面分割为单题
4. **自动标注**：调用LLM分析题目，标注难度、题型和知识点
5. **结果输出**：将有效题目保存为JSON格式

## 注意事项

1. **数学公式**：OCR会将数学公式转换为LaTeX格式，如 `$\sin^2\alpha + \cos^2\beta = 1$`
2. **无效题目**：以下情况会被标记为无效并丢弃：
   - 页头/页尾被截断的不完整题目
   - 题干中明确说明需要参考图片的题目
3. **并行数**：根据API速率限制调整batch_size，建议5-16之间
4. **内存占用**：PDF转图片步骤可能占用较多内存，大文件建议分批处理

## 支持的题型

- 单选题
- 多选题
- 填空题
- 计算题
- 证明题
- 应用题

## 支持的知识点

### 高等数学
- 数列极限、函数极限、无穷小比较
- 连续性、导数定义、求导法则
- 微分中值定理、泰勒展开
- 函数性态分析、洛必达法则
- 不定积分、定积分、变限积分
- 反常积分、几何应用、物理应用
- 微分方程、多元函数微分学
- 二重积分、三重积分、曲线曲面积分
- 级数敛散性、幂级数、傅里叶级数

### 线性代数
- 行列式、矩阵运算、逆矩阵
- 矩阵的秩、向量组线性相关性
- 线性方程组、特征值与特征向量
- 相似矩阵、二次型

### 概率论与数理统计
- 随机事件与概率
- 随机变量及其分布
- 多维随机变量
- 数字特征、大数定律
- 统计量及其分布
- 参数估计、假设检验


