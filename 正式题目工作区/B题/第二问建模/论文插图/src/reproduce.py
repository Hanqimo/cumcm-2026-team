"""Recompute all figure data, export three figures and record artifact checks."""
from pathlib import Path
import csv, hashlib, json, os, platform, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def record_manifest():
    import matplotlib
    import numpy
    import pypdf
    from PIL import Image

    outputs = {}
    for path in sorted((ROOT / 'output').glob('*.pdf')):
        reader = pypdf.PdfReader(path)
        assert len(reader.pages) == 1
        page = reader.pages[0]
        fonts = []
        for reference in page['/Resources']['/Font'].get_object().values():
            font = reference.get_object()
            descendants = font.get('/DescendantFonts')
            for face in descendants if descendants else [font]:
                face = face.get_object()
                descriptor = face.get('/FontDescriptor')
                assert descriptor is not None
                descriptor = descriptor.get_object()
                embedded = any(key in descriptor for key in ['/FontFile', '/FontFile2', '/FontFile3'])
                assert embedded, f'Font not embedded in {path.name}'
                fonts.append({'name': str(face['/BaseFont']), 'embedded': embedded})
        text = page.extract_text()
        assert any('\u4e00' <= c <= '\u9fff' for c in text), 'Chinese text must survive PDF export.'
        with Image.open(path.with_suffix('.png')) as png:
            size = list(png.size)
            dpi = list(png.info['dpi'])
            assert all(abs(d - 600) < 1 for d in dpi)
        assert path.with_suffix('.svg').exists()
        outputs[path.stem] = {'pdf_pages': 1, 'page_points': [float(page.mediabox.width), float(page.mediabox.height)],
                             'embedded_fonts': fonts, 'png_pixels': size, 'png_dpi': dpi}
    assert len(outputs) == 3
    files = {}
    for path in sorted(ROOT.rglob('*')):
        rel = path.relative_to(ROOT)
        if not path.is_file() or 'build' in rel.parts or '__pycache__' in rel.parts:
            continue
        if str(rel) in ['manifest.json', 'src/worst_backend.hpp']:
            continue
        files[str(rel)] = sha(path)
    result = {'python': sys.version.split()[0], 'platform': platform.platform(),
              'versions': {'numpy': numpy.__version__, 'matplotlib': matplotlib.__version__, 'pypdf': pypdf.__version__},
              'source_contract': json.loads((ROOT / 'input_contract.json').read_text()),
              'outputs': outputs, 'sha256': files}
    (ROOT / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('Verified three single-page PDFs with embedded fonts, 600-dpi PNGs and SVG exports.')

def main():
    for name, digest in json.loads((ROOT / 'input_contract.json').read_text()).items():
        assert sha(ROOT.parent / name) == digest, f'Source changed: {name}; review the inputs first.'
    env = dict(os.environ)
    env.setdefault('MPLCONFIGDIR', str(ROOT / 'build' / 'mplconfig'))
    for script in ['prepare_data.py', 'draw_figures.py', 'check_data.py']:
        subprocess.run([sys.executable, str(ROOT / 'src' / script)], env=env, check=True)
    record_manifest()

if __name__ == '__main__':
    main()
