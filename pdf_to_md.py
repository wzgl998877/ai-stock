# -*- coding: utf-8 -*-
"""
PDF 转 Markdown 工具（文本型 PDF，含图片提取，无需 OCR）

原理：
  1. 文字：page.get_text("dict") 按坐标取文字块
  2. 图片：page.get_images() + get_image_rects() 取图片及其在页面上的位置
  3. 把“文字块”和“图片”都带上 (y, x) 坐标，排序后产出阅读顺序的 token 流
  4. 段落合并：上一行不以结束标点结尾则与下一行拼接（修复跨页断句）
  5. 图片按实际像素尺寸过滤（默认 ≥300×200），丢掉页眉/装饰条等假图
  6. “数字：”开头的短行识别为章节标题（针对缠论 108 课，其它文档可删）

依赖：pip install pymupdf
用法：python pdf_to_md.py [输入.pdf] [输出.md]
示例：python pdf_to_md.py 缠中说禅108课.pdf 缠中说禅108课.md
"""
import sys
import os
import re
import shutil
import fitz  # PyMuPDF

MIN_W, MIN_H = 300, 200          # 图片最小像素尺寸，过滤装饰条/页眉
END_PUNCT = set("。！？；：”』）)…\"'!?;:】》")
TITLE_RE = re.compile(r"^(\d{1,3})[：:]\s*(.+)$")


def block_lines(b):
    out = []
    for line in b.get("lines", []):
        s = "".join(sp.get("text", "") for sp in line.get("spans", [])).strip()
        if s:
            out.append(s)
    return out


def convert(src: str, dst: str) -> None:
    img_dir = os.path.splitext(dst)[0] + "_images"
    if os.path.isdir(img_dir):
        shutil.rmtree(img_dir)
    os.makedirs(img_dir, exist_ok=True)

    doc = fitz.open(src)
    n = doc.page_count

    # 第 1 遍：按页 → 按 (y, x) 排序 block，产出 token 流（文字行 / 图片文件名）
    tokens, xref_to_file = [], []
    saved = {}
    for pno in range(n):
        page = doc[pno]
        items = []
        for b in page.get_text("dict")["blocks"]:                       # 文字
            if b.get("type") == 0:
                ls = block_lines(b)
                if ls:
                    items.append((b["bbox"][1], b["bbox"][0], "t", ls))
        for info in page.get_images(full=True):                          # 图片
            xref = info[0]
            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []
            if not rects:
                rects = [fitz.Rect(0, 1e7, 0, 1e7)]                      # 无位置 → 排到页末
            if xref not in saved:
                try:
                    im = doc.extract_image(xref)
                    if im.get("width", 0) < MIN_W or im.get("height", 0) < MIN_H:
                        continue                                          # 过滤装饰条
                    ext = im.get("ext", "png")
                    fname = f"p{pno+1:03d}_{xref}.{ext}"
                    with open(os.path.join(img_dir, fname), "wb") as f:
                        f.write(im["image"])
                    saved[xref] = fname
                except Exception:
                    continue
            if xref in saved:
                for r in rects:
                    items.append((r.y0, r.x0, "i", saved[xref]))
        items.sort(key=lambda x: (round(x[0], 1), x[1]))
        for y, x, k, v in items:
            tokens.append((k, v))

    # 第 2 遍：段落合并 + 标题识别 + 图文穿插
    parts = [f"# {os.path.basename(src)}\n"]
    lessons = [0]
    buf = ""

    def emit(para):
        m = TITLE_RE.match(para)
        if m and len(para) < 70:
            num = m.group(1)
            rest = re.sub(r"\(?\s*\d{4}-\d{2}-\d{2}.*$", "", m.group(2)).strip(" 　!！")
            if rest:
                parts.append(f"\n## 第 {num} 课　{rest}")
                lessons[0] += 1
                return
        parts.append(para)

    for k, v in tokens:
        if k == "t":
            for ln in v:
                if buf and buf[-1] in END_PUNCT:
                    emit(buf); buf = ln
                elif buf:
                    buf += ln
                else:
                    buf = ln
        else:                                                            # 图片独立成段
            if buf:
                emit(buf); buf = ""
            parts.append(f"![图]({os.path.basename(img_dir)}/{v})")
    if buf:
        emit(buf)

    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n\n".join(parts))
    print(f"完成：{n} 页，{len(saved)} 张图，{lessons[0]} 个标题 -> {dst}")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "缠中说禅108课.pdf"
    dst = sys.argv[2] if len(sys.argv) > 2 else src.rsplit(".", 1)[0] + ".md"
    convert(src, dst)
