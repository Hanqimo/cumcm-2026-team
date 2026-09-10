"""Build the CUMCM paper library and its machine-readable index."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "resources" / "papers"
TMP_ROOT = ROOT / "tmp" / "pdfs" / "paper-library"

PAPER_INDEXES = {
    2025: ["https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2025qgdxssxjmjslwzs/"],
    2024: ["https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2024qgdxssxjmjslwzs/"],
    2023: [
        "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2023qgdxssxjmjslwzs/",
        "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2023qgdxssxjmjslwzs/2023gjsbqgdxssxjmjslwzs.shtml",
    ],
    2022: [
        "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2022qgdxssxjmjslwzs/",
        "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2022qgdxssxjmjslwzs/2022gjsbqgdxssxjmjslwzs.shtml",
    ],
    2021: [
        "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2021qgdxssxjmjslwzs/",
        "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2021qgdxssxjmjslwzs/2021gjsbqgdxssxjmjslwzs.shtml",
    ],
}

REVIEW_SEEDS = [
    "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmstjp/",
    "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmstjp/gjsbqgdxssxjmjsstjp.shtml",
    "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmstjp/2023sxjmstjp/2023qgdxssxjmjsstjp.shtml",
    "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmstjp/2022sxjmstjp/2022gjsbqgdxssxjmjsstjp.shtml",
    "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmstjp/2023sxjmjsbjc/",
    "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmstjp/2022sxjmjsbjc/",
]

AWARD_PDFS = {
    2025: "https://www.mcm.edu.cn/upload_cn/node/767/He1YI4ZEe969ff168945f43e52721891ab19945b.pdf",
    2024: "https://www.mcm.edu.cn/upload_cn/node/733/4rFKQqyT96ee1e63dd8d2408e56df8b2ec172125.pdf",
    2023: "https://www.mcm.edu.cn/upload_cn/node/701/6XE4ZF5Oc3573e0779f6cd8e31d79a6e9f6fd13d.pdf",
    2022: "https://www.mcm.edu.cn/upload_cn/node/629/uJzoCRK40ebedd130f42ed41e5f144ac29bae490.pdf",
    2021: "https://www.mcm.edu.cn/upload_cn/node/626/n7nhofCn201ab6d8d92db35564daa7cca31853d6.pdf",
}

NAMED_AWARDS = [
    {"year": 2025, "award": "本科组高教社杯", "team": "张新晨、徐威南、周诗贺", "school": "清华大学"},
    {"year": 2024, "award": "本科组高教社杯", "team": "唐梓轩、陈欣雨、杨一汀", "school": "北京师范大学"},
    {"year": 2024, "award": "本科组北太天元数模之星", "team": "陈静怡、陈诺严、游天明", "school": "上海交通大学"},
    {"year": 2023, "award": "本科组高教社杯", "team": "曹宇轩、黄瑞、秦一天", "school": "复旦大学"},
    {"year": 2022, "award": "本科组高教社杯", "team": "曹菁文、栾天成、康文广", "school": "山东大学"},
    {"year": 2021, "award": "本科组高教社杯", "team": "王凯伦、高原、黄琬", "school": "西南交通大学"},
]

GITHUB_PAPERS = [
    {
        "repo": "CUMCM-2025B-Team/CUMCM-2025-Problem-B",
        "paths": ["25国赛.pdf"],
        "year": 2025,
        "problem": "B",
        "name": "2025-B-github-CUMCM-2025-Problem-B.pdf",
        "award_claim": "仓库自述：全国一等奖",
        "local_cache": "tmp/pdfs/candidate-papers/2025-B-national-first.pdf",
    },
    {
        "repo": "cny123222/CUMCM-2024A-Bench-Dragon",
        "paths": ["OurPaper.pdf"],
        "year": 2024,
        "problem": "A",
        "name": "2024-A-github-Bench-Dragon.pdf",
        "award_claim": "仓库自述：全国一等奖、北太天元数模之星",
        "local_cache": "tmp/pdfs/candidate-papers/2024-A-national-first-special.pdf",
    },
    {
        "repo": "linggm3/2023_CUMCM_National-First-Prize",
        "paths": ["定日镜场优化设计模型.pdf"],
        "year": 2023,
        "problem": "A",
        "name": "2023-A-github-National-First-Prize.pdf",
        "award_claim": "仓库自述：全国一等奖",
        "local_cache": "tmp/pdfs/candidate-papers/2023-A-national-first.pdf",
    },
    {
        "repo": "Arctic1010/CUMCM2024-A",
        "paths": ["example (2).pdf"],
        "year": 2024,
        "problem": "A",
        "name": "2024-A-github-Arctic1010.pdf",
        "award_claim": "仓库自述：全国一等奖",
        "local_cache": "tmp/pdfs/candidate-papers/2024-A-national-first-2.pdf",
    },
    {
        "repo": "xyfJASON/CUMCM-2021-A",
        "paths": ["thesis/thesis(contest).pdf"],
        "year": 2021,
        "problem": "A",
        "name": "2021-A-github-contest.pdf",
        "award_claim": "仓库自述：广东赛区一等奖",
    },
    {
        "repo": "xyfJASON/CUMCM-2021-A",
        "paths": ["thesis/thesis(revised).pdf"],
        "year": 2021,
        "problem": "A",
        "name": "2021-A-github-post-contest-revised.pdf",
        "award_claim": "赛后修订稿；原参赛稿仓库自述为广东赛区一等奖",
    },
    {
        "repo": "gbh1234/CUMCM2024B",
        "paths": ["论文/基于抽样检测与优化决策的企业生产过程质量控制模型研究.pdf"],
        "year": 2024,
        "problem": "B",
        "name": "2024-B-github-Jiangsu-First-Prize.pdf",
        "award_claim": "仓库自述：江苏赛区一等奖",
    },
    {
        "repo": "qfpqhyl/CUMCM2023B",
        "paths": ["B 多波束测深系统的条带覆盖宽度及重叠率的数值模拟与分析 史鸿宇 郭心仪 田博松.pdf"],
        "year": 2023,
        "problem": "B",
        "name": "2023-B-github-Hebei-First-Prize.pdf",
        "award_claim": "仓库自述：河北赛区一等奖",
    },
    {
        "repo": "du2279664786/CUMCM",
        "paths": ["C题/C题.docx"],
        "year": 2022,
        "problem": "C",
        "name": "2022-C-github-Shandong-First-Prize.pdf",
        "award_claim": "仓库自述：山东赛区一等奖",
        "source_format": "docx",
        "entry_type": "github_support_note",
        "content_note": "仓库未公开完整参赛论文；该DOCX仅3页，包含赛题说明、分析提纲和代码片段",
    },
    {
        "repo": "LXYHBU/2025-CUMCM-ProblemC-Provincial-1st",
        "paths": ["doc/report.pdf"],
        "year": 2025,
        "problem": "C",
        "name": "2025-C-github-Provincial-First-Prize.pdf",
        "award_claim": "仓库自述：省一等奖",
    },
]


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=5, backoff_factor=0.8, status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "CUMCM-local-paper-library/1.0"})
    return s


HTTP = session()


def get(url: str, *, timeout: int = 45) -> requests.Response:
    response = HTTP.get(url, timeout=timeout)
    response.raise_for_status()
    return response


def clean_text(value: str) -> str:
    return " ".join(value.split())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(LIBRARY).as_posix()


def pdf_info(path: Path) -> dict[str, Any]:
    reader = PdfReader(str(path))
    return {
        "local_path": relative(path),
        "pages": len(reader.pages),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def discover_papers() -> list[dict[str, Any]]:
    found: dict[tuple[int, str], dict[str, Any]] = {}
    pattern = re.compile(r"(202[1-5]).*?([A-E])题论文展示[（(]([A-E]\d+)[）)]")
    for year, urls in PAPER_INDEXES.items():
        for index_url in urls:
            soup = BeautifulSoup(get(index_url).text, "html.parser")
            for anchor in soup.select("a[href]"):
                title = clean_text(anchor.get_text(" ", strip=True))
                match = pattern.search(title)
                if not match:
                    continue
                code = match.group(3).upper()
                found[(year, code)] = {
                    "type": "official_paper",
                    "year": year,
                    "problem": match.group(2),
                    "code": code,
                    "title": title,
                    "source_url": urljoin(index_url, anchor["href"]),
                    "award": "官方展示论文；公开获奖名单未提供论文编号到参赛队的映射，无法仅凭编号核验奖级",
                    "award_verification": "unmapped-official-display-id",
                }
    return sorted(found.values(), key=lambda x: (x["year"], x["problem"], x["code"]))


def article_images(url: str, code: str | None = None) -> tuple[str, list[str], str]:
    soup = BeautifulSoup(get(url).text, "html.parser")
    page_title = clean_text((soup.title.get_text(" ", strip=True) if soup.title else ""))
    images: list[str] = []
    seen: set[str] = set()
    for image in soup.select("img[src]"):
        alt = clean_text(image.get("alt", ""))
        src = urljoin(url, image["src"])
        looks_like_page = "页面" in alt or bool(code and code.lower() in alt.lower())
        if looks_like_page and src not in seen:
            images.append(src)
            seen.add(src)
    article = soup.select_one(".article") or soup.select_one("article") or soup.body
    text = clean_text(article.get_text("\n", strip=True) if article else "")
    return page_title, images, text


def image_extension(response: requests.Response, url: str) -> str:
    content_type = response.headers.get("Content-Type", "").lower()
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def download_one_image(index: int, url: str, directory: Path) -> Path:
    response = get(url, timeout=90)
    suffix = image_extension(response, url)
    target = directory / f"{index:04d}{suffix}"
    target.write_bytes(response.content)
    with Image.open(target) as image:
        image.verify()
    return target


def images_to_pdf(image_paths: list[Path], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    document = canvas.Canvas(str(output), pagesize=A4, pageCompression=1)
    for path in image_paths:
        with Image.open(path) as image:
            width, height = image.size
        page_size = landscape(A4) if width > height else A4
        page_width, page_height = page_size
        document.setPageSize(page_size)
        scale = min(page_width / width, page_height / height)
        draw_width = width * scale
        draw_height = height * scale
        x = (page_width - draw_width) / 2
        y = (page_height - draw_height) / 2
        document.drawImage(ImageReader(str(path)), x, y, draw_width, draw_height, preserveAspectRatio=True)
        document.showPage()
    document.save()
    pages = len(PdfReader(str(output)).pages)
    if pages != len(image_paths):
        raise RuntimeError(f"page-count mismatch for {output}: {pages} != {len(image_paths)}")


def safe_remove_tmp(directory: Path) -> None:
    resolved = directory.resolve()
    root = TMP_ROOT.resolve()
    if root not in resolved.parents:
        raise RuntimeError(f"refusing to remove temp directory outside {root}: {resolved}")
    if directory.exists():
        def make_writable_and_retry(function: Any, path: str, _exc_info: Any) -> None:
            os.chmod(path, stat.S_IWRITE)
            function(path)

        shutil.rmtree(directory, onerror=make_writable_and_retry)


def build_article_pdf(url: str, output: Path, *, code: str | None = None) -> tuple[str, str]:
    title, images, text = article_images(url, code)
    if not images:
        raise RuntimeError(f"no page images found: {url}")
    if output.exists() and output.stat().st_size > 10_000:
        return title, text
    tmp = TMP_ROOT / output.stem
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        completed: dict[int, Path] = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(download_one_image, i, image_url, tmp): i for i, image_url in enumerate(images, 1)}
            for future in as_completed(futures):
                completed[futures[future]] = future.result()
        ordered = [completed[i] for i in range(1, len(images) + 1)]
        images_to_pdf(ordered, output)
    finally:
        safe_remove_tmp(tmp)
    return title, text


def download_official_papers(limit: int | None = None) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    papers = discover_papers()
    if limit:
        papers = papers[:limit]
    print(f"Discovered {len(papers)} official display papers", flush=True)
    for number, paper in enumerate(papers, 1):
        output = LIBRARY / paper["problem"] / str(paper["year"]) / f"{paper['year']}-{paper['code']}-official-display.pdf"
        try:
            print(f"[{number}/{len(papers)}] official {paper['year']} {paper['code']}", flush=True)
            build_article_pdf(paper["source_url"], output, code=paper["code"])
            paper.update(pdf_info(output))
            entries.append(paper)
        except Exception as exc:  # continue so a transient source failure does not lose completed work
            failures.append({"kind": "official_paper", "source": paper["source_url"], "error": str(exc)})
            print(f"ERROR official {paper['code']}: {exc}", file=sys.stderr, flush=True)
    return entries, failures


def discover_reviews() -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for seed in REVIEW_SEEDS:
        soup = BeautifulSoup(get(seed).text, "html.parser")
        for anchor in soup.select("a[href]"):
            title = clean_text(anchor.get_text(" ", strip=True))
            url = urljoin(seed, anchor["href"])
            match = re.search(r"(202[2-5]).*(讲评|颁奖词|AI工具)", title)
            if not match or "/zx/a/" not in url:
                continue
            problem_match = re.search(r"([A-E])题", title)
            kind = "award_commentary" if "颁奖词" in title else "review"
            found[url] = {
                "type": kind,
                "year": int(match.group(1)),
                "problem": problem_match.group(1) if problem_match else "GENERAL",
                "title": title,
                "source_url": url,
            }
    return sorted(found.values(), key=lambda x: (x["year"], x["problem"], x["title"]))


def download_reviews() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    reviews = discover_reviews()
    print(f"Discovered {len(reviews)} official review/commentary items", flush=True)
    for number, item in enumerate(reviews, 1):
        article_id = Path(urlparse(item["source_url"]).path).stem
        label = "award-commentary" if item["type"] == "award_commentary" else "review"
        output_dir = LIBRARY / "reviews" / str(item["year"]) / item["problem"]
        pdf_path = output_dir / f"{item['year']}-{item['problem']}-{label}-{article_id}.pdf"
        md_path = output_dir / f"{item['year']}-{item['problem']}-{label}-{article_id}.md"
        try:
            print(f"[{number}/{len(reviews)}] {label} {item['year']} {item['problem']}", flush=True)
            title, images, text = article_images(item["source_url"])
            output_dir.mkdir(parents=True, exist_ok=True)
            md_path.write_text(
                f"# {item['title']}\n\n- 来源：{item['source_url']}\n- 保存日期：{date.today().isoformat()}\n\n{text}\n",
                encoding="utf-8",
            )
            if images:
                build_article_pdf(item["source_url"], pdf_path)
                item.update(pdf_info(pdf_path))
            else:
                item.update(
                    {
                        "local_path": relative(md_path),
                        "pages": None,
                        "bytes": md_path.stat().st_size,
                        "sha256": sha256(md_path),
                    }
                )
            item["markdown_path"] = relative(md_path)
            entries.append(item)
        except Exception as exc:
            failures.append({"kind": item["type"], "source": item["source_url"], "error": str(exc)})
            print(f"ERROR review {item['source_url']}: {exc}", file=sys.stderr, flush=True)
    return entries, failures


def download_pdf(url: str, output: Path) -> None:
    if output.exists() and output.stat().st_size > 10_000:
        return
    response = get(url, timeout=120)
    if not response.content.startswith(b"%PDF"):
        raise RuntimeError(f"download is not a PDF: {url}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)
    PdfReader(str(output))


def github_file(repo: str, path: str, output: Path) -> dict[str, Any]:
    api_url = f"https://api.github.com/repos/{repo}/contents/{quote(path, safe='/')}"
    metadata = get(api_url).json()
    download_url = metadata.get("download_url")
    if not download_url:
        raise RuntimeError(f"GitHub did not return a download URL for {repo}:{path}")
    completed = subprocess.run(
        [
            "curl.exe",
            "-L",
            "--fail",
            "--retry",
            "5",
            "--retry-all-errors",
            "--max-time",
            "600",
            "--silent",
            "--show-error",
            "--output",
            str(output),
            download_url,
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=660,
    )
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"curl failed for {repo}:{path}: {error}")
    return metadata


def convert_docx_to_pdf(docx_path: Path, output: Path) -> None:
    bundled_python = Path(
        r"C:\Users\kaiyi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    )
    renderer = Path(
        r"C:\Users\kaiyi\.codex\plugins\cache\openai-primary-runtime\documents\26.818.11542\skills\documents\render_docx.py"
    )
    render_dir = docx_path.parent / "rendered"
    render_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [str(bundled_python), str(renderer), str(docx_path), "--output_dir", str(render_dir), "--emit_pdf"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if completed.returncode == 0:
        rendered_pdf = render_dir / f"{docx_path.stem}.pdf"
        if not rendered_pdf.exists():
            candidates = list(render_dir.glob("*.pdf"))
            if len(candidates) != 1:
                raise RuntimeError(f"DOCX renderer did not produce one PDF in {render_dir}")
            rendered_pdf = candidates[0]
        shutil.copy2(rendered_pdf, output)
    else:
        # The bundled renderer needs LibreOffice. On this Windows workspace,
        # Word is available and provides a faithful local conversion fallback.
        escaped_input = str(docx_path.resolve()).replace("'", "''")
        escaped_output = str(output.resolve()).replace("'", "''")
        command = (
            "$word=New-Object -ComObject Word.Application; $word.Visible=$false; "
            "try { $doc=$word.Documents.Open('" + escaped_input + "',$false,$true); "
            "$doc.SaveAs2('" + escaped_output + "',17); $doc.Close($false) } "
            "finally { $word.Quit() }"
        )
        word = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
        )
        if word.returncode != 0 or not output.exists():
            render_message = (completed.stdout + completed.stderr).decode("utf-8", errors="replace")
            word_message = (word.stdout + word.stderr).decode("utf-8", errors="replace")
            raise RuntimeError(
                f"DOCX conversion failed via LibreOffice and Word. "
                f"LibreOffice: {render_message[-800:]} Word: {word_message[-800:]}"
            )
    PdfReader(str(output))


def merge_pdfs(inputs: list[Path], output: Path) -> None:
    writer = PdfWriter()
    for path in inputs:
        for page in PdfReader(str(path)).pages:
            writer.add_page(page)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)


def download_github_papers() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    print(f"Configured {len(GITHUB_PAPERS)} GitHub paper files", flush=True)
    for number, spec in enumerate(GITHUB_PAPERS, 1):
        entry_type = spec.get("entry_type", "github_paper")
        if entry_type == "github_paper":
            output = LIBRARY / spec["problem"] / str(spec["year"]) / spec["name"]
        else:
            output = LIBRARY / "support" / str(spec["year"]) / spec["name"]
        try:
            print(f"[{number}/{len(GITHUB_PAPERS)}] GitHub {spec['repo']}", flush=True)
            if not output.exists() or output.stat().st_size < 10_000:
                cache = ROOT / spec["local_cache"] if spec.get("local_cache") else None
                if cache and cache.exists():
                    output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(cache, output)
                    PdfReader(str(output))
                    print(f"  reused verified local cache: {cache.name}", flush=True)
                else:
                    tmp = TMP_ROOT / f"github-{number}"
                    tmp.mkdir(parents=True, exist_ok=True)
                    parts: list[Path] = []
                    try:
                        clone_dir = tmp / "repo"
                        clone = subprocess.run(
                            [
                                "git",
                                "clone",
                                "--depth",
                                "1",
                                f"https://github.com/{spec['repo']}.git",
                                str(clone_dir),
                            ],
                            check=False,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=300,
                        )
                        if clone.returncode != 0:
                            message = (clone.stdout + clone.stderr).decode("utf-8", errors="replace")
                            raise RuntimeError(f"git clone failed for {spec['repo']}: {message[-2000:]}")
                        for part_number, source_path in enumerate(spec["paths"], 1):
                            suffix = ".docx" if spec.get("source_format") == "docx" else ".pdf"
                            part = tmp / f"part-{part_number}{suffix}"
                            source = clone_dir / Path(source_path)
                            if not source.exists():
                                raise RuntimeError(f"missing cloned source file: {source_path}")
                            shutil.copy2(source, part)
                            parts.append(part)
                        if spec.get("source_format") == "docx":
                            if len(parts) != 1:
                                raise RuntimeError("DOCX GitHub paper must have exactly one source file")
                            convert_docx_to_pdf(parts[0], output)
                        elif len(parts) == 1:
                            output.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(parts[0], output)
                            PdfReader(str(output))
                        else:
                            merge_pdfs(parts, output)
                    finally:
                        safe_remove_tmp(tmp)
            repo_metadata = get(f"https://api.github.com/repos/{spec['repo']}").json()
            entry = {
                "type": entry_type,
                "year": spec["year"],
                "problem": spec["problem"],
                "title": spec["name"].removesuffix(".pdf"),
                "source_url": f"https://github.com/{spec['repo']}",
                "source_files": spec["paths"],
                "award": spec["award_claim"],
                "award_verification": "repository-self-reported",
                "license": (repo_metadata.get("license") or {}).get("spdx_id") or "NOASSERTION",
            }
            if spec.get("content_note"):
                entry["content_note"] = spec["content_note"]
            entry.update(pdf_info(output))
            entries.append(entry)
        except Exception as exc:
            failures.append({"kind": "github_paper", "source": spec["repo"], "error": str(exc)})
            print(f"ERROR GitHub {spec['repo']}: {exc}", file=sys.stderr, flush=True)
    return entries, failures


def download_awards() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for year, url in AWARD_PDFS.items():
        output = LIBRARY / "awards" / f"{year}-official-awards.pdf"
        try:
            print(f"award list {year}", flush=True)
            download_pdf(url, output)
            entry = {
                "type": "award_list",
                "year": year,
                "problem": "GENERAL",
                "title": f"{year}高教社杯全国大学生数学建模竞赛获奖名单",
                "source_url": url,
            }
            entry.update(pdf_info(output))
            entries.append(entry)
        except Exception as exc:
            failures.append({"kind": "award_list", "source": url, "error": str(exc)})
            print(f"ERROR award list {year}: {exc}", file=sys.stderr, flush=True)
    return entries, failures


def markdown_link(path: str) -> str:
    return f"[{Path(path).name}]({quote(path, safe='/')})"


def write_indexes(entries: list[dict[str, Any]], failures: list[dict[str, str]]) -> None:
    entries = sorted(entries, key=lambda x: (x.get("problem", ""), -int(x.get("year", 0)), x.get("type", ""), x.get("title", "")))
    payload = {
        "generated_on": date.today().isoformat(),
        "library_root": "resources/papers",
        "source_note": "资料应保留原始来源、核验状态和文件摘要，提交前人工检查重复项与文件大小。",
        "award_mapping_note": "公开获奖名单不含匿名论文编号，无法仅凭A163/B060等编号可靠匹配参赛队与奖级。",
        "named_awards": NAMED_AWARDS,
        "entries": entries,
        "failures": failures,
    }
    (LIBRARY / "index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    official_count = sum(item["type"] == "official_paper" for item in entries)
    github_count = sum(item["type"] == "github_paper" for item in entries)
    support_count = sum(item["type"] == "github_support_note" for item in entries)
    review_count = sum(item["type"] in {"review", "award_commentary"} for item in entries)
    lines = [
        "# CUMCM 优秀论文资料库",
        "",
        f"> 更新日期：{date.today().isoformat()}。当前收录：官方展示论文 {official_count} 篇、GitHub 完整论文 {github_count} 份、GitHub 不完整材料 {support_count} 份、官方讲评/颁奖词 {review_count} 项。",
        "",
        "## 使用与核验说明",
        "",
        "- 资料应保留原始来源、核验状态、页数、字节数和 SHA-256，提交前人工检查重复项与文件大小。",
        "- 官网获奖名单只列学校、队员和指导教师，不列匿名论文编号。A163、B060 等编号无法直接对应奖级，索引统一标记为“官方展示，奖级未公开映射”。",
        "- GitHub 项目的奖项来自仓库作者自述，除非作者身份与官方名单能够闭环，否则不提升为“官方核验”。",
        "- `index.json` 保存机器可读的来源、页数、字节数和 SHA-256，可用于后续增量维护。",
        "",
        "重新抓取或补全：",
        "",
        "```powershell",
        "python .\\resources\\papers\\fetch_library.py",
        "```",
        "",
    ]
    for problem in "ABCDE":
        problem_entries = [item for item in entries if item.get("problem") == problem and item["type"] in {"official_paper", "github_paper"}]
        lines.extend([f"## {problem} 题", "", "| 年份 | 类型/编号 | 本地文件 | 奖项核验 | 来源 |", "|---:|---|---|---|---|"])
        for item in sorted(problem_entries, key=lambda x: (-x["year"], x["type"], x.get("code", ""))):
            label = f"官方展示 {item.get('code', '')}" if item["type"] == "official_paper" else "GitHub论文"
            lines.append(
                f"| {item['year']} | {label} | {markdown_link(item['local_path'])} | {item.get('award', '')} | [原始来源]({item['source_url']}) |"
            )
        lines.append("")

    lines.extend(["## 官方讲评与颁奖词", "", "| 年份 | 题目 | 类型 | 本地文件 | 来源 |", "|---:|---|---|---|---|"])
    review_entries = [item for item in entries if item["type"] in {"review", "award_commentary"}]
    for item in sorted(review_entries, key=lambda x: (-x["year"], x["problem"], x["title"])):
        lines.append(
            f"| {item['year']} | {item['problem']} | {item['title']} | {markdown_link(item['local_path'])} | [官网]({item['source_url']}) |"
        )
    support_entries = [item for item in entries if item["type"] == "github_support_note"]
    lines.extend(["", "## 不完整或不能作为论文认定的材料", ""])
    for item in support_entries:
        lines.append(
            f"- {item['year']} {item['problem']}题：[本地材料]({quote(item['local_path'], safe='/')})；"
            f"{item.get('content_note', '不是完整论文')}。[仓库]({item['source_url']})"
        )
    lines.extend(["", "## 冠名奖（独立官方名单）", "", "这些奖项可由官方名单确认，但公开资料不足以把获奖队与匿名展示编号逐篇匹配。", "", "| 年份 | 奖项 | 队员 | 学校 |", "|---:|---|---|---|"])
    for award in sorted(NAMED_AWARDS, key=lambda x: (-x["year"], x["award"])):
        lines.append(f"| {award['year']} | {award['award']} | {award['team']} | {award['school']} |")
    lines.extend(["", "## 下载异常", ""])
    if failures:
        for failure in failures:
            lines.append(f"- `{failure['kind']}` {failure['source']}: {failure['error']}")
    else:
        lines.append("- 无。")
    lines.append("")
    (LIBRARY / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-official", type=int, default=None, help="download only the first N official papers (for testing)")
    parser.add_argument("--skip-official", action="store_true")
    parser.add_argument("--skip-reviews", action="store_true")
    parser.add_argument("--skip-github", action="store_true")
    parser.add_argument("--skip-awards", action="store_true")
    args = parser.parse_args()

    LIBRARY.mkdir(parents=True, exist_ok=True)
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    if not args.skip_official:
        new_entries, new_failures = download_official_papers(args.limit_official)
        entries.extend(new_entries)
        failures.extend(new_failures)
    if not args.skip_reviews:
        new_entries, new_failures = download_reviews()
        entries.extend(new_entries)
        failures.extend(new_failures)
    if not args.skip_github:
        new_entries, new_failures = download_github_papers()
        entries.extend(new_entries)
        failures.extend(new_failures)
    if not args.skip_awards:
        new_entries, new_failures = download_awards()
        entries.extend(new_entries)
        failures.extend(new_failures)

    write_indexes(entries, failures)
    print(f"Completed: {len(entries)} indexed items; {len(failures)} failures", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
