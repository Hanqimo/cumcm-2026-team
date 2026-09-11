"""Hash all retained evidence, excluding generated Python caches and this index itself."""
from pathlib import Path
import json,hashlib,datetime
p=Path(__file__).resolve().parents[1];files=[]
for f in sorted(p.rglob('*')):
 if not f.is_file() or '__pycache__' in f.parts or f.name=='artifact_manifest.json':continue
 files.append({'path':str(f.relative_to(p)),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
out={'created':datetime.datetime.now().astimezone().isoformat(),'file_count':len(files),'total_bytes':sum(f['bytes'] for f in files),'files':files}
(p/'artifact_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(out['file_count'],out['total_bytes'])
