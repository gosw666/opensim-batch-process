# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 导入必要的模块
import os
import sys

# 获取当前工作目录
current_dir = os.getcwd()

# 获取 conda 环境路径（构建时使用）
conda_prefix = os.environ.get('CONDA_PREFIX', '')
if not conda_prefix:
    conda_prefix = r'C:\Users\17256\miniconda3\envs\opensim_scripting'

opensim_path = os.path.join(conda_prefix, 'Lib', 'opensim')
library_bin_path = os.path.join(conda_prefix, 'Library', 'bin')
numpy_path = os.path.join(conda_prefix, 'Lib', 'site-packages', 'numpy')
scipy_path = os.path.join(conda_prefix, 'Lib', 'site-packages', 'scipy')
matplotlib_path = os.path.join(conda_prefix, 'Lib', 'site-packages', 'matplotlib')

# 确保路径存在
if not os.path.exists(opensim_path):
    print(f"OpenSim path not found: {opensim_path}")
    sys.exit(1)

# 获取所有必要的DLL文件
binaries = []
# 收集 Library\bin 目录下的所有 DLL
if os.path.exists(library_bin_path):
    for root, dirs, files in os.walk(library_bin_path):
        for file in files:
            if file.endswith('.dll'):
                # 计算相对路径，确保正确的输出目录结构
                rel_path = os.path.relpath(root, library_bin_path)
                if rel_path == '.':
                    dest_dir = 'Library\\bin'
                else:
                    dest_dir = os.path.join('Library\\bin', rel_path)
                binaries.append((os.path.join(root, file), dest_dir))

# 收集 Python DLL
python_dll = os.path.join(os.path.dirname(sys.executable), 'python311.dll')
if os.path.exists(python_dll):
    binaries.append((python_dll, '.'))

# 收集其他可能需要的系统 DLL
# 这里可以添加更多需要的 DLL 文件

a = Analysis(['main_gui.py'],
             pathex=[current_dir],  # 使用当前目录作为搜索路径
             binaries=binaries,
             datas=[
                 (opensim_path, 'opensim'), 
                 ('beiti.png', '.'),
                 # 添加OpenSim依赖的DLL文件
                 (library_bin_path, 'Library\\bin'),
                 # 添加必要的Python库
                 (numpy_path, 'numpy'),
                 (scipy_path, 'scipy'),
                 (matplotlib_path, 'matplotlib'),
                 # 添加Geometry目录
                 ('Geometry', 'Geometry'),
             ],  # 包含OpenSim库和logo图片
             hiddenimports=[
                 'gui_ast_tab', 'gui_id_tab', 'gui_ik_tab', 'gui_so_tab', 'gui_c3d_tab',
                 'numpy', 'scipy', 'matplotlib', 'numpy.core._dtype_ctypes', 'opensim',
                 'numpy.core._methods', 'numpy.lib.format', 'numpy.linalg._umath_linalg',
                 'scipy.sparse._sparsetools', 'scipy.linalg._fblas', 'scipy.linalg._flapack',
                 'scipy.linalg._solve_toeplitz', 'scipy.linalg._decomp_lu',
                 'scipy.linalg._matfuncs_expm', 'scipy.optimize._trlib', 'scipy.optimize._lbfgsb',
                 'scipy.optimize._moduleTNC', 'scipy.optimize._cobyla', 'scipy.optimize._slsqp',
                 'scipy.optimize._trustregion_constr', 'scipy.optimize._minimize',
                 'scipy.integrate._odepack', 'scipy.integrate._quadpack', 'scipy.special._ufuncs',
                 'scipy.special._specfun', 'scipy.special._comb',
                 'scipy.spatial._ckdtree', 'scipy.spatial._qhull', 'scipy.spatial._voronoi',
                 'scipy.sparse.linalg._dsolve._superlu',
                 'matplotlib.backends.backend_qtagg', 'matplotlib.figure', 'matplotlib.axes',
                 'matplotlib.lines', 'matplotlib.patches', 'matplotlib.text', 'matplotlib.collections',
                 'matplotlib.colors', 'matplotlib.cm', 'matplotlib.ticker', 'matplotlib.gridspec',
                 'matplotlib.transforms', 'matplotlib.contour', 'matplotlib.path', 'matplotlib.spines',
                 'matplotlib.axis', 'matplotlib._tight_layout', 'matplotlib.font_manager',
                 'matplotlib.style', 'matplotlib.rcsetup', 'matplotlib.pyplot',
             ],

             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
# 方案1：单文件模式（现有）
# 优点：分发方便，只需一个EXE文件
# 缺点：每个实例会生成2GB的临时目录
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='main_gui',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,  # 禁用UPX压缩，避免DLL文件损坏
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,  # 显示命令行窗口，便于调试
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          onefile=True)  # 使用单文件模式

# 方案2：目录模式
# 优点：依赖只存储一次，启动更快，节省磁盘空间
# 缺点：分发时需要复制整个目录
# 取消注释下面的代码来使用目录模式
# 并注释掉上面的单文件模式代码
# executable = EXE(pyz,
#           a.scripts,
#           a.binaries,
#           a.zipfiles,
#           a.datas,
#           [],
#           name='main_gui',
#           debug=False,
#           bootloader_ignore_signals=False,
#           strip=False,
#           upx=False,  # 禁用UPX压缩，避免DLL文件损坏
#           upx_exclude=[],
#           runtime_tmpdir=None,
#           console=True,  # 显示命令行窗口，便于调试
#           disable_windowed_traceback=False,
#           target_arch=None,
#           codesign_identity=None,
#           entitlements_file=None,
#           onefile=False)  # 使用目录模式

# # 添加COLLECT语句以生成目录结构
# coll = COLLECT(executable,
#                a.binaries,
#                a.zipfiles,
#                a.datas,
#                strip=False,
#                upx=False,
#                name='main_gui')
