# Reproducible onedir build: no Python/Node installation needed by the user.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

project = Path(SPECPATH)
mp_data, mp_bins, mp_hidden = collect_all('mediapipe')
datas = [(str(project / 'dist'), 'dist'),
         (str(project / 'assets/models'), 'assets/models'),
         (str(project / 'assets/avatars/sample.vrm'), 'assets/avatars'),
         (str(project / 'assets/avatars/AvatarSample_A.vrm'), 'assets/avatars'),
         (str(project / 'assets/avatars/AvatarSample_A-source.txt'), 'assets/avatars'),
         (str(project / 'assets/avatars/SAMPLE-README.md'), 'assets/avatars'),
         (str(project / 'UPSTREAM-LICENSE'), '.'),
         (str(project / 'desktop-assets/app.ico'), 'desktop-assets')]
a = Analysis([str(project / 'desktop.py')], pathex=[str(project)],
             binaries=mp_bins, datas=datas + mp_data + collect_data_files('webview'),
             hiddenimports=mp_hidden + ['webview.platforms.winforms', 'webview.platforms.edgechromium',
                                       'scipy.spatial.transform', 'numpy', 'clr_loader'],
             excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'gtk', 'gi', 'torch', 'tensorflow',
                       'jax', 'pytest', 'IPython', 'notebook'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='AvatarStudio',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, icon=str(project / 'desktop-assets/app.ico'),
          version=str(project / 'desktop-assets/version.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='AvatarStudio')
