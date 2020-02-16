# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['kathara.py'],
             pathex=['../src/'],
             binaries=[],
             datas=[],
             hiddenimports=['Resources',
                            'Resources.command',
                            'Resources.command.CheckCommand',
                            'Resources.command.ConnectCommand',
                            'Resources.command.LcleanCommand',
                            'Resources.command.LinfoCommand',
                            'Resources.command.ListCommand',
                            'Resources.command.LrestartCommand',
                            'Resources.command.LstartCommand',
                            'Resources.command.LtestCommand',
                            'Resources.command.LconfigCommand',
                            'Resources.command.SettingsCommand',
                            'Resources.command.VcleanCommand',
                            'Resources.command.VconfigCommand',
                            'Resources.command.VstartCommand',
                            'Resources.command.WipeCommand',
                            'Resources.manager.ManagerProxy',
                            'Resources.manager.docker.DockerManager'
                            ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='kathara',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          icon='app_icon.ico'
           )