"""Verify and restore exact run evidence without replacing different local files."""
import argparse,hashlib,json,zipfile
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parent


def digest(data):return hashlib.sha256(data).hexdigest()


def destination_path(root,name):
    relative=PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe archive path')
    target=(root/Path(*relative.parts)).resolve()
    if root!=target and root not in target.parents:raise ValueError('Path outside destination')
    return target


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--verify-only',action='store_true',help='Check hashes without writing files')
    ap.add_argument('--model',help='Restore one model, e.g. q4/m02-adaptive-cover')
    ap.add_argument('--destination',type=Path,default=ROOT,help='Optional clean destination for complete evidence tree')
    args=ap.parse_args();target_root=args.destination.resolve()
    manifest=json.loads((ROOT/'归档清单.json').read_text(encoding='utf-8'))
    selected=[a for a in manifest['archives'] if not args.model or a['model']==args.model]
    if args.model and not selected:raise ValueError('Unknown model')
    members={f['path']:f for f in manifest['files']};restored=0;verified=0
    # Uncompressed mathematical models and source files also retain original bytes.
    for f in manifest['files']:
        if f['archive'] is None:
            source=ROOT/Path(f['path']);data=source.read_bytes()
            if digest(data)!=f['sha256']:raise ValueError('Changed source: '+f['path'])
            verified+=1
            if not args.verify_only and target_root!=ROOT:
                target=destination_path(target_root,f['path'])
                if target.exists():
                    if digest(target.read_bytes())!=f['sha256']:raise FileExistsError(target)
                else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    for archive in selected:
        path=ROOT/Path(archive['path'])
        if digest(path.read_bytes())!=archive['sha256']:raise ValueError('Archive hash mismatch')
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                f=members[info.filename]
                if f['archive']!=archive['path']:raise ValueError('Unexpected archive member')
                target=destination_path(target_root,info.filename);data=z.read(info)
                if len(data)!=f['bytes'] or digest(data)!=f['sha256']:raise ValueError('Member hash mismatch')
                verified+=1
                if args.verify_only:continue
                if target.exists():
                    if digest(target.read_bytes())!=f['sha256']:raise FileExistsError('Refusing to replace '+str(target))
                else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);restored+=1
    print(json.dumps(dict(verified_files=verified,restored_run_files=restored,archives=len(selected),verify_only=args.verify_only)))


if __name__=='__main__':main()
