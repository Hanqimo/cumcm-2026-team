from pathlib import Path
import subprocess,sys,json,shutil,re
from pypdf import PdfReader
import pypdfium2 as pdfium
ROOT=Path(__file__).resolve().parents[1];repo=ROOT.parents[5]
# ROOT.parents[5] is repository; derive robustly from known relative directory.
repo=next(p for p in ROOT.parents if (p/'templates/论文模版.tex').exists())
shutil.copy2(ROOT.parent/'build/第二问模型.pdf',ROOT.parent/'第二问模型.pdf')
reports={}
for name in ['q2_posterior','q2_feedback','q2_candidates']:
 for ext in ['pdf','png','svg']:
  src=ROOT/f'figures/{name}.{ext}';out=ROOT/f'verification/{name}_{ext}_metadata.json'
  args=[sys.executable,str(ROOT/'skill/scripts/image_metadata.py'),str(src),'--format',ext,'--target-width-mm','160','--output',str(out),'--force']
  if ext=='png':args+=['--mode','RGB','--min-dpi','599.8','--alpha-policy','forbid']
  proc=subprocess.run(args,capture_output=True,text=True)
  if proc.returncode:raise RuntimeError(proc.stdout+proc.stderr)
# Render PDFs, not only Matplotlib PNG exports; record page-level figure occurrence.
paths=[repo/'templates/论文模版.pdf',repo/'梳理/论文初稿.pdf',ROOT.parent/'第二问模型.pdf']
needles=['首次正常示向度观测前后的位置信息','第二次反馈的预测分布与剩余区域','11个权重下的候选检测点及评价指标']
for pdf in paths:
 reader=PdfReader(pdf);texts=[p.extract_text() or '' for p in reader.pages];normalized=[re.sub(r'\s+','',t) for t in texts];pages=[i for i,t in enumerate(normalized) if any(n in t for n in needles)]
 assert all(sum(n in t for t in normalized)==1 for n in needles),(str(pdf),pages)
 reports[str(pdf.relative_to(repo))]={'pages':len(reader.pages),'figure_pages':[i+1 for i in pages]}
 (ROOT/f'verification/{pdf.stem}_text.txt').write_text('\n\n'.join(f'PAGE {i+1}\n{t}' for i,t in enumerate(texts)))
 doc=pdfium.PdfDocument(str(pdf))
 for i in pages:
  page=doc[i];im=page.render(scale=1.5).to_pil();im.save(ROOT/f'verification/{pdf.stem}_page_{i+1}.png');page.close()
 doc.close()
for name in ['q2_posterior','q2_feedback','q2_candidates']:
 pdf=ROOT/f'figures/{name}.pdf';doc=pdfium.PdfDocument(str(pdf));page=doc[0];page.render(scale=2.5).to_pil().save(ROOT/f'verification/{name}_pdf_render.png');page.close();doc.close()
(ROOT/'verification/pdf_pages.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2))
print(json.dumps(reports,ensure_ascii=False,indent=2))
