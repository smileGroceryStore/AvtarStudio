"""Add usage notes and dependency license texts to the portable release."""
from pathlib import Path
from importlib.metadata import distributions
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'release-passthrough/AvatarStudio'

def main():
    shutil.copy2(ROOT / 'DESKTOP-README.txt', DEST / '使用说明.txt')
    lines = ['Avatar Studio 0.8 Blink And Arms — Third-party notices',
             'Upstream tracking: https://github.com/DarkStar1997/vtubing (MIT)',
             'See _internal/UPSTREAM-LICENSE.',
             'Models: see _internal/assets/avatars/ for model-specific source and terms.',
             '', 'JavaScript:',
             'Three.js 0.169.0 — MIT — https://github.com/mrdoob/three.js',
             '@pixiv/three-vrm 3.5.5 — MIT — https://github.com/pixiv/three-vrm', '']
    for package in ['three', '@pixiv/three-vrm']:
        for name in ['LICENSE', 'LICENSE.txt']:
            license_file = ROOT / 'node_modules' / package / name
            if license_file.exists():
                lines += [f'=== {package} ===', license_file.read_text('utf-8', errors='replace'), '']
                break
    for dist in sorted(distributions(), key=lambda d: d.metadata.get('Name', '')):
        name = dist.metadata.get('Name', '')
        if not name or name.lower() in ('avatar-studio', 'pyinstaller', 'pyinstaller-hooks-contrib', 'setuptools'):
            continue
        lines += [f'=== {name} {dist.version} ===', dist.metadata.get('Home-page', ''),
                  dist.metadata.get('License-Expression', dist.metadata.get('License', 'See license below'))]
        for file in dist.files or []:
            if file.name.lower().startswith(('license', 'copying', 'notice')):
                path = Path(dist.locate_file(file))
                if path.is_file() and path.stat().st_size < 1024 * 1024:
                    lines += [str(file), path.read_text('utf-8', errors='replace')]
        lines.append('')
    (DEST / 'THIRD-PARTY-NOTICES.txt').write_text('\n'.join(lines), 'utf-8')

if __name__ == '__main__':
    main()
