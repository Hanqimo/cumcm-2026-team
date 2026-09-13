from pathlib import Path
import sys,re,json,subprocess,shutil,hashlib
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];repo=Path(json.loads((ROOT/'inputs/revision.json').read_text())['root']);old=ROOT.parent/'论文插图_20260913'
shutil.copy2(ROOT.parent/'build/第二问模型.pdf',ROOT.parent/'第二问模型.pdf')
for name,width in [('q2_posterior_general',160),('q2_feedback_distribution',150),('q2_feedback_regions',130)]:
 for ext in ['pdf','png','svg']:
  args=[sys.executable,str(old/'skill/scripts/image_metadata.py'),str(ROOT/f'figures/{name}.{ext}'),'--format',ext,'--target-width-mm',str(width),'--output',str(ROOT/f'verification/{name}_{ext}_metadata.json'),'--force']
  if ext=='png':args+=['--mode','RGB','--min-dpi','599.7','--alpha-policy','forbid']
  run=subprocess.run(args,capture_output=True,text=True);assert run.returncode==0,run.stdout+run.stderr
needle=['非圆心检测点处','两种示向度反馈下的剩余区域','第二次示向度的预测密度及满足完成条件的反馈','11个权重下的候选检测点']
reports={}
for path in [repo/'templates/论文模版.pdf',repo/'梳理/论文初稿.pdf',ROOT.parent/'第二问模型.pdf']:
 reader=PdfReader(path);texts=[re.sub(r'\s+','',p.extract_text()) for p in reader.pages];indices=[i for i,t in enumerate(texts) if any(n in t for n in needle)]
 assert all(sum(n in t for t in texts)==1 for n in needle)
 reports[str(path.relative_to(repo))]={'pages':len(texts),'figure_pages':[i+1 for i in indices]}
 doc=pdfium.PdfDocument(str(path))
 for i in indices:
  page=doc[i];page.render(scale=1.5).to_pil().save(ROOT/f'verification/{path.stem}_page_{i+1}.png');page.close()
 doc.close()
 (ROOT/f'verification/{path.stem}_text.txt').write_text('\n\n'.join(f'PAGE {i+1}\n{p.extract_text()}' for i,p in enumerate(reader.pages)))
for name in ['q2_posterior_general','q2_feedback_distribution','q2_feedback_regions']:
 doc=pdfium.PdfDocument(str(ROOT/f'figures/{name}.pdf'));page=doc[0];page.render(scale=2.5).to_pil().save(ROOT/f'verification/{name}_pdf.png');page.close();doc.close()
for i in reports['templates/论文模版.pdf']['figure_pages']:
 assert ImageChops.difference(Image.open(ROOT/f'verification/论文模版_page_{i}.png'),Image.open(ROOT/f'verification/论文初稿_page_{i}.png')).getbbox() is None
(ROOT/'verification/pdf_pages.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2));print(json.dumps(reports,ensure_ascii=False,indent=2))
