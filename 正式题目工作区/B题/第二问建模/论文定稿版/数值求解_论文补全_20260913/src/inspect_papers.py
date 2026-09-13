from pathlib import Path
import json,re,shutil
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];repo=next(p for p in ROOT.parents if (p/'templates/论文模版.tex').exists());model=ROOT.parent
shutil.copy2(model/'build/第二问模型.pdf',model/'第二问模型.pdf')
needles=['第一步：构造区域与搜索范围','第二步：计算一个检测点的评价值','第三步：搜索优选位置','第四步：复算与核验','典型首次观测下的数值优选点','原点、正东算例中不同权重的选点与定位效果','11个权重下的候选检测点及评价指标']
reports={}
for p in [repo/'templates/论文模版.pdf',repo/'梳理/论文初稿.pdf',model/'第二问模型.pdf']:
 doc=PdfReader(p);texts=[x.extract_text() or '' for x in doc.pages];norm=[re.sub(r'\s+','',x) for x in texts];indices=[i for i,x in enumerate(norm) if any(t in x for t in needles)]
 assert all(any(t in x for x in norm) for t in needles)
 (ROOT/f'verification/{p.stem}_text.txt').write_text('\n\n'.join(f'PAGE {i+1}\n{x}' for i,x in enumerate(texts)))
 render=pdfium.PdfDocument(str(p))
 for i in indices:
  page=render[i];page.render(scale=1.5).to_pil().save(ROOT/f'verification/{p.stem}_page_{i+1}.png');page.close()
 render.close();reports[str(p.relative_to(repo))]={'pages':len(texts),'new_content_pages':[i+1 for i in indices]}
for i in reports['templates/论文模版.pdf']['new_content_pages']:
 assert ImageChops.difference(Image.open(ROOT/f'verification/论文模版_page_{i}.png'),Image.open(ROOT/f'verification/论文初稿_page_{i}.png')).getbbox() is None
(ROOT/'verification/pdf_pages.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2));print(json.dumps(reports,ensure_ascii=False,indent=2))
