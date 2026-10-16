"""Copy the Python game package and map data into docs/ for the GitHub Pages site."""
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent.parent
docs = root / 'docs'

py_dir = docs / 'py' / 'game'
if py_dir.parent.exists():
    shutil.rmtree(py_dir.parent, ignore_errors=True)
py_dir.mkdir(parents=True)
files = sorted(p.name for p in (root / 'game').glob('*.py'))
for name in files:
    shutil.copy(root / 'game' / name, py_dir / name)

data_dir = docs / 'data'
data_dir.mkdir(exist_ok=True)
shutil.copy(root / 'data' / 'maps' / 'classic_map.json', data_dir / 'classic_map.json')

(docs / 'py' / 'manifest.json').write_text(
    '[' + ', '.join(f'"game/{n}"' for n in files) + ']')
print(f'Built site files: {len(files)} python modules')
