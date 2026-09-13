from pathlib import Path
import json,math,re,subprocess,shutil,hashlib
import numpy as np
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import Image,ImageChops,ImageDraw
ROOT=Path(__file__).resolve().parents[1];model=ROOT.parent;repo=next(p for p in ROOT.parents if (p/'templates/论文模版.tex').exists());shutil.copy2(model/'build/第二问模型.pdf',model/'第二问模型.pdf')
params=json.loads((ROOT/'data/general_posterior_parameters.json').read_text());posterior=[]
for b in [30.,90.]:
 info=json.loads(subprocess.check_output([str(ROOT/'base_solver'),'1200',str(b),'info'],text=True));expected=params['C1_m2'][str(b)];assert abs(info['C1']-expected)<1e-6
 arr=np.load(ROOT/f'data/posterior_beta_{int(b)}.npz');r=arr['distance_m'];angle=arr['relative_angle_deg'];den=arr['density_per_m2'];x=1200+r[None,:]*np.cos(np.deg2rad(b+angle[:,None]));y=r[None,:]*np.sin(np.deg2rad(b+angle[:,None]));assert np.all(den[x*x+y*y>1800**2+1e-8]==0);assert np.all(den[abs(angle)>1]==0)
 posterior.append({'beta_deg':b,'C1_analytic':expected,'C1_geometric':info['C1'],'density_max':float(den.max())})
(ROOT/'verification/posterior_checks.json').write_text(json.dumps(posterior,indent=2))
files=[repo/'templates/论文模版.pdf',repo/'梳理/论文初稿.pdf',model/'第二问模型.pdf'];reports={}
for path in files:
 reader=PdfReader(path);texts=[x.extract_text() or '' for x in reader.pages];text='\n'.join(texts);assert '原地完成光学' not in text and '定位损失的定义' in re.sub(r'\s+','',text)
 first=0 if path.parent==model else next(i for i,x in enumerate(texts) if '问题二的模型与求解' in re.sub(r'\s+','',x))
 last=len(texts)-1 if path.parent==model else next(i for i,x in enumerate(texts) if '问题三的模型与求解' in re.sub(r'\s+','',x))-1
 doc=pdfium.PdfDocument(str(path));ims=[]
 for i in range(first,last+1):
  page=doc[i];im=page.render(scale=1.35).to_pil();im.save(ROOT/f'verification/{path.stem}_page_{i+1}.png');page.close();thumb=im.copy();thumb.thumbnail((440,623));canvas=Image.new('RGB',(460,650),'white');canvas.paste(thumb,((460-thumb.width)//2,24));ImageDraw.Draw(canvas).text((15,5),f'Page {i+1}',fill='black');ims.append(canvas)
 cols=3;rows=math.ceil(len(ims)/cols);sheet=Image.new('RGB',(460*cols,650*rows),'#dddddd')
 for j,im in enumerate(ims):sheet.paste(im,((j%cols)*460,(j//cols)*650))
 sheet.save(ROOT/f'verification/{path.stem}_contact.png');doc.close();(ROOT/f'verification/{path.stem}_text.txt').write_text(text)
 reports[str(path.relative_to(repo))]={'pages':len(texts),'q2_pages':list(range(first+1,last+2))}
main=pdfium.PdfDocument(str(files[0]));draft=pdfium.PdfDocument(str(files[1]));assert len(main)==len(draft)
for i in range(len(main)):
 p1=main[i];p2=draft[i];assert ImageChops.difference(p1.render(scale=1).to_pil(),p2.render(scale=1).to_pil()).getbbox() is None;p1.close();p2.close()
main.close();draft.close();(ROOT/'verification/pdf_pages.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2));print(reports)
# Export properties for final-size manuscript figures.
metadata={}
for pdf in sorted((ROOT/'figures').glob('*.pdf')):
 p=PdfReader(pdf).pages[0];im=Image.open(pdf.with_suffix('.png'));fonts=[]
 for v in p['/Resources'].get('/Font',{}).values():
  f=v.get_object();desc=f.get('/FontDescriptor');desc=desc.get_object() if desc else None
  if not desc and f.get('/DescendantFonts'):desc=f['/DescendantFonts'][0].get_object().get('/FontDescriptor').get_object()
  fonts.append({'name':str(f.get('/BaseFont')),'embedded':bool(desc and any(k in desc for k in ['/FontFile','/FontFile2','/FontFile3']))})
 assert all(z['embedded'] for z in fonts)
 metadata[pdf.stem]={'width_mm':float(p.mediabox.width)*25.4/72,'height_mm':float(p.mediabox.height)*25.4/72,'raster_mode':im.mode,'raster_size':im.size,'dpi':im.info.get('dpi'),'fonts':fonts}
 assert im.mode=='RGB' and min(im.info['dpi'])>599
(ROOT/'verification/figure_export_metadata.json').write_text(json.dumps(metadata,indent=2))
