"""text_chunker 单元测试"""

from app.domain.services.text_chunker import chunk_article


class TestChunkArticle:

    def test_empty_content(self):
        """content 为空或 None，只返回 chunk_0"""
        result = chunk_article("标题", "摘要", "")
        assert len(result) == 1
        assert result[0].chunk_type == "summary"

        result = chunk_article("标题", "摘要", None)
        assert len(result) == 1

        result = chunk_article("标题", "摘要", "   ")
        assert len(result) == 1

    def test_title_summary_chunk(self):
        """chunk_0 始终是 title + summary，chunk_type='summary'"""
        result = chunk_article("光伏行业分析", "光伏行业前景良好", "## 正文")
        assert result[0].index == 0
        assert result[0].content == "光伏行业分析\n光伏行业前景良好"
        assert result[0].chunk_type == "summary"

    def test_single_section(self):
        """只有一个 ## 章节，返回 chunk_0 + chunk_1"""
        content = "## 事件背景\n这是一段背景介绍。"
        result = chunk_article("标题", "摘要", content)
        assert len(result) == 2
        assert result[1].chunk_type == "content"
        assert result[1].content.startswith("## 事件背景")

    def test_multiple_sections(self):
        """多个 ## 章节各自成为独立 chunk"""
        content = "## 事件背景\n背景内容\n\n## 影响逻辑\n逻辑内容\n\n## 风险提示\n风险内容"
        result = chunk_article("标题", "摘要", content)
        assert len(result) == 4  # chunk_0 + 3 sections
        assert all(c.chunk_type == "content" for c in result[1:])
        assert result[1].content.startswith("## 事件背景")
        assert result[2].content.startswith("## 影响逻辑")
        assert result[3].content.startswith("## 风险提示")

    def test_section_with_table(self):
        """包含 Markdown 表格的章节不被拆散"""
        content = (
            "## 产业链传导表\n"
            "| 行业 | 影响 |\n"
            "|------|------|\n"
            "| 电力设备 | 受益 |\n"
            "| 煤炭 | 受损 |\n"
        )
        result = chunk_article("标题", "摘要", content)
        assert len(result) == 2
        assert "| 电力设备 | 受益 |" in result[1].content
        assert "| 煤炭 | 受损 |" in result[1].content

    def test_oversized_section_split(self):
        """超过 max_size 的章节按段落二次拆分"""
        long_para = "这是一段很长的文字。" * 200  # ~1600 字
        content = f"## 超长章节\n{long_para}\n\n这是第二段文字。"
        result = chunk_article("标题", "摘要", content, max_size=800)
        assert len(result) > 2  # chunk_0 + 多个 content chunk
        assert all(c.chunk_type == "content" for c in result[1:])

    def test_content_without_headers(self):
        """content 无 ## 标题但有正文，整体作为一个 chunk"""
        content = "这是第一段。\n\n这是第二段。\n\n这是第三段。"
        result = chunk_article("标题", "摘要", content)
        assert len(result) == 2  # chunk_0 + 整个 content 作为 chunk_1
        assert result[1].chunk_type == "content"

    def test_chunk_index_sequential(self):
        """chunk index 从 0 开始连续递增"""
        content = "## A\n内容A\n\n## B\n内容B\n\n## C\n内容C"
        result = chunk_article("标题", "摘要", content)
        indices = [c.index for c in result]
        assert indices == list(range(len(result)))

    def test_mixed_h2_h3(self):
        """## 和 ### 混合时只按 ## 切分，### 保留在章节内"""
        content = "## 主章节\n正文\n\n### 子标题\n子正文\n\n## 另一章节\n另一正文"
        result = chunk_article("标题", "摘要", content)
        assert len(result) == 3  # chunk_0 + 2 sections
        assert "### 子标题" in result[1].content
        assert "子正文" in result[1].content
