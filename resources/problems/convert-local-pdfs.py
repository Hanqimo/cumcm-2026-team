"""Convert downloaded problem PDFs into searchable Markdown text."""

from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent
LIBRARY_ROOT = ROOT / "library"
MARKDOWN_ROOT = ROOT / "markdown"


def convert_pdf(pdf_path: Path, output_path: Path) -> None:
    reader = PdfReader(str(pdf_path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"## 第 {index} 页\n\n{text.strip()}\n")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"# {pdf_path.stem}\n\n"
        "> 本文件由官方 PDF 自动抽取，仅供本地检索；公式、图片和排版请以原 PDF 为准。\n\n"
        + "\n".join(pages),
        encoding="utf-8",
    )


def main() -> None:
    pdfs = [
        path
        for letter in "ABCDE"
        for path in (LIBRARY_ROOT / letter).rglob("*.pdf")
    ]
    if not pdfs:
        raise SystemExit(
            "未找到 PDF。请先运行 resources/problems/download-official.ps1。"
        )

    for pdf_path in sorted(pdfs):
        relative = pdf_path.relative_to(LIBRARY_ROOT)
        output_path = (MARKDOWN_ROOT / relative).with_suffix(".md")
        convert_pdf(pdf_path, output_path)
        print(f"Converted: {relative}")


if __name__ == "__main__":
    main()
