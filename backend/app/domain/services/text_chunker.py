"""文章切分服务 — 按 Markdown ## 章节级切分"""

import re

from app.domain.entities.vector_search import Chunk


def chunk_article(
    title: str,
    summary: str,
    content: str,
    max_size: int = 1500,
) -> list[Chunk]:
    """将文章按 Markdown ## 章节切分为语义 chunk 列表。

    切分规则：
        - chunk_0 始终是 title + summary（保留标题级匹配能力）
        - content 按 ## 标题分段，每个章节作为一个独立 chunk
        - 超过 max_size 的章节按 \\n\\n 段落二次拆分

    Args:
        title: 文章标题
        summary: 文章摘要
        content: Markdown 格式正文（由 LLM 生成，含 ## 章节结构）
        max_size: 单个 chunk 最大字符数，默认 1500

    Returns:
        始终返回至少一个 Chunk（chunk_0 = title + summary）。
        若正文为空或只有空白，只返回 chunk_0。
    """
    # chunk_0：标题 + 摘要块
    chunks = [Chunk(index=0, content=f"{title}\n{summary}", chunk_type="summary")]

    if not content or not content.strip():
        return chunks

    # 按 ## 标题分段
    sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    chunk_index = 1

    for section in sections:
        if len(section) <= max_size:
            chunks.append(Chunk(index=chunk_index, content=section, chunk_type="content"))
            chunk_index += 1
        else:
            # 超长章节按段落二次拆分
            paragraphs = section.split("\n\n")
            buffer = ""

            for para in paragraphs:
                merged = buffer + "\n\n" + para if buffer else para

                if len(merged) <= max_size:
                    buffer = merged
                else:
                    if buffer:
                        chunks.append(Chunk(index=chunk_index, content=buffer, chunk_type="content"))
                        chunk_index += 1
                    buffer = para

            if buffer:
                chunks.append(Chunk(index=chunk_index, content=buffer, chunk_type="content"))
                chunk_index += 1

    return chunks
