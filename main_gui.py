"""
main_gui.py - 统一的AST-IK-ID-SO批处理GUI主窗口
集成AST缩放、IK逆运动学、ID逆动力学和SO功能四个模块
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import sys
import os
import importlib
import time
import json
import tempfile
import atexit
import shutil

# 添加当前目录到路径，以便导入其他模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 临时目录管理
temp_dir = None
TEMP_DIR_NAME = "opensim_temp"

def cleanup_temp():
    """清理临时目录"""
    global temp_dir
    if temp_dir and os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            print(f"清理临时目录：{temp_dir}")
        except Exception as e:
            print(f"清理临时目录失败：{e}")

def cleanup_old_temp():
    """清理旧的临时目录（智能清理：能删的删，不能删的跳过）"""
    temp_root = tempfile.gettempdir()
    target_temp_dir = os.path.join(temp_root, TEMP_DIR_NAME)
    
    # 如果目标临时目录存在，尝试清理其中的内容
    if os.path.exists(target_temp_dir):
        print(f"开始清理临时目录：{target_temp_dir}")
        
        # 遍历临时目录中的所有文件和文件夹
        for root, dirs, files in os.walk(target_temp_dir, topdown=False):
            # 先清理文件
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.unlink(file_path)
                    print(f"删除文件：{file_path}")
                except Exception:
                    # 文件被占用，跳过
                    print(f"跳过占用的文件：{file_path}")
            
            # 再清理文件夹
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                try:
                    os.rmdir(dir_path)
                    print(f"删除文件夹：{dir_path}")
                except Exception:
                    # 文件夹被占用或不为空，跳过
                    print(f"跳过占用的文件夹：{dir_path}")
        
        # 最后尝试删除根临时目录
        try:
            os.rmdir(target_temp_dir)
            print(f"删除临时目录：{target_temp_dir}")
        except Exception:
            # 目录被占用或不为空，跳过
            print(f"跳过占用的临时目录：{target_temp_dir}")

# 初始化临时目录
def init_temp_dir():
    """初始化临时目录"""
    global temp_dir
    temp_root = tempfile.gettempdir()
    temp_dir = os.path.join(temp_root, TEMP_DIR_NAME)
    
    # 确保临时目录存在
    os.makedirs(temp_dir, exist_ok=True)
    print(f"使用临时目录：{temp_dir}")

# 启动时清理旧临时文件并初始化临时目录
cleanup_old_temp()
init_temp_dir()

# 注册退出时清理
atexit.register(cleanup_temp)

from gui_ast_tab import ASTTab
from gui_ik_tab import IKTab
from gui_id_tab import IDTab
from gui_so_tab import SOTab
from gui_c3d_tab import C3DTab
# from gui_ai_tab import AITab






class MainGUI:
    """主GUI窗口类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("OpenSim AST-IK-ID-SO 批处理工具")
        # 移除固定窗口大小，让窗口可以自动缩放
        # self.root.geometry("1200x800")
        
        # 设置粉色主题
        self.setup_pink_theme()
        
        # 创建界面
        self.create_widgets()
        
        # 设置窗口最小尺寸
        self.root.minsize(800, 600)
        
        # 绑定窗口大小变化事件
        self.root.bind('<Configure>', self.on_configure)
    
    def setup_pink_theme(self):
        """设置粉色主题"""
        # 设置主窗口背景色为浅粉色
        self.root.configure(bg='#FFE4E1')  # LavenderBlush
        
        # 创建自定义样式
        style = ttk.Style()
        
        # 设置主题
        try:
            style.theme_use('clam')  # 使用clam主题作为基础
        except:
            pass
        
        # 定义粉色配色方案
        pink_bg = '#FFE4E1'      # LavenderBlush - 浅粉色背景
        pink_button = '#FFB6C1'  # LightPink - 按钮背景
        pink_active = '#FF69B4'  # HotPink - 激活状态
        pink_text = '#8B008B'    # DarkMagenta - 深紫色文字
        pink_frame = '#FFC0CB'   # Pink - 框架背景
        
        # 配置Frame样式
        style.configure('TFrame', background=pink_bg)
        style.configure('TLabel', background=pink_bg, foreground=pink_text, font=('Microsoft YaHei', 9))
        style.configure('TButton', background=pink_button, foreground=pink_text, font=('Microsoft YaHei', 9, 'bold'))
        style.map('TButton',
                  background=[('active', pink_active), ('pressed', '#FF1493')])
        style.configure('TCheckbutton', background=pink_bg, foreground=pink_text, font=('Microsoft YaHei', 9))
        style.configure('TNotebook', background=pink_bg)
        style.configure('TNotebook.Tab', background=pink_frame, foreground=pink_text, font=('Microsoft YaHei', 9, 'bold'))
        style.map('TNotebook.Tab',
                  background=[('selected', pink_button), ('active', pink_active)])
        style.configure('TSeparator', background=pink_frame)
        
        # 配置LabelFrame样式
        style.configure('TLabelframe', background=pink_bg, font=('Microsoft YaHei', 10, 'bold'))
        style.configure('TLabelframe.Label', background=pink_frame, foreground=pink_text, font=('Microsoft YaHei', 10, 'bold'))
        
        # 存储各个标签页的引用
        self.ast_tab = None
        self.ik_tab = None
        self.id_tab = None
        self.so_tab = None
        self.c3d_tab = None
        # self.ai_tab = None
    
    def create_widgets(self):
        """创建GUI组件"""
        # 顶部框架：logo和操作按钮
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        # 添加logo
        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "beiti.png")
            print(f"尝试加载logo路径: {logo_path}")
            print(f"文件是否存在: {os.path.exists(logo_path)}")
            self.logo_image = tk.PhotoImage(file=logo_path)
            logo_label = ttk.Label(top_frame, image=self.logo_image, background='#FFE4E1')
            logo_label.pack(side=tk.LEFT, padx=10)
            print("logo加载成功")
        except Exception as e:
            print(f"无法加载logo: {e}")
        
        # 添加重载模块按钮
        self.reload_btn = ttk.Button(
            top_frame,
            text="重载模块",
            command=self.reload_modules
        )
        self.reload_btn.pack(side=tk.RIGHT, padx=10)
        
        # 分隔线
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=5)
        
        # 创建标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # C3D转换标签页
        c3d_frame = ttk.Frame(self.notebook)
        self.notebook.add(c3d_frame, text="C3D 转换")
        self.c3d_tab = C3DTab(c3d_frame)
        
        # AST标签页
        ast_frame = ttk.Frame(self.notebook)
        self.notebook.add(ast_frame, text="AST 模型缩放")
        self.ast_tab = ASTTab(ast_frame)
        
        # IK标签页
        ik_frame = ttk.Frame(self.notebook)
        self.notebook.add(ik_frame, text="IK 逆运动学")
        self.ik_tab = IKTab(ik_frame)
        
        # ID标签页
        id_frame = ttk.Frame(self.notebook)
        self.notebook.add(id_frame, text="ID 逆动力学")
        self.id_tab = IDTab(id_frame)
        
        # SO标签页
        so_frame = ttk.Frame(self.notebook)
        self.notebook.add(so_frame, text="SO 静态优化")
        self.so_tab = SOTab(so_frame)
        
        # AI聊天标签页 - 暂时隐藏
        # ai_frame = ttk.Frame(self.notebook)
        # self.notebook.add(ai_frame, text="AI 助手")
        # self.ai_tab = AITab(ai_frame)
        

    

    
    def reload_modules(self):
        """重新加载所有模块，实现热更新"""
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 重新加载导入的模块
            import gui_ast_tab
            import gui_ik_tab
            import gui_id_tab
            import gui_so_tab
            import gui_c3d_tab
            # import gui_ai_tab
            
            importlib.reload(gui_ast_tab)
            importlib.reload(gui_ik_tab)
            importlib.reload(gui_id_tab)
            importlib.reload(gui_so_tab)
            importlib.reload(gui_c3d_tab)
            # importlib.reload(gui_ai_tab)
            
            # 重新创建标签页
            self.recreate_tabs()
            
            # 计算耗时
            elapsed_time = time.time() - start_time
            
            messagebox.showinfo("成功", f"模块重载完成！耗时: {elapsed_time:.2f}秒")
        except Exception as e:
            import traceback
            error_msg = f"模块重载失败:\n{str(e)}\n\n{traceback.format_exc()}"
            print(error_msg)
            messagebox.showerror("错误", error_msg)
    


    
    def on_configure(self, event):
        """窗口大小变化时的处理函数"""
        # 当窗口大小变化时，notebook会自动适应
        pass
    
    def recreate_tabs(self):
        """重新创建所有标签页"""
        # 保存当前选中的标签页
        current_tab = None
        if hasattr(self, 'notebook'):
            try:
                current_tab = self.notebook.index(self.notebook.select())
            except:
                current_tab = 0
            
            # 销毁旧的notebook
            self.notebook.destroy()
        
        # 重新导入模块
        from gui_ast_tab import ASTTab
        from gui_ik_tab import IKTab
        from gui_id_tab import IDTab
        from gui_so_tab import SOTab
        from gui_c3d_tab import C3DTab
        # from gui_ai_tab import AITab
        
        # 创建新的notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # C3D转换标签页
        c3d_frame = ttk.Frame(self.notebook)
        self.notebook.add(c3d_frame, text="C3D 转换")
        self.c3d_tab = C3DTab(c3d_frame)
        
        # AST标签页
        ast_frame = ttk.Frame(self.notebook)
        self.notebook.add(ast_frame, text="AST 模型缩放")
        self.ast_tab = ASTTab(ast_frame)
        
        # IK标签页
        ik_frame = ttk.Frame(self.notebook)
        self.notebook.add(ik_frame, text="IK 逆运动学")
        self.ik_tab = IKTab(ik_frame)
        
        # ID标签页
        id_frame = ttk.Frame(self.notebook)
        self.notebook.add(id_frame, text="ID 逆动力学")
        self.id_tab = IDTab(id_frame)
        
        # SO标签页
        so_frame = ttk.Frame(self.notebook)
        self.notebook.add(so_frame, text="SO 静态优化")
        self.so_tab = SOTab(so_frame)
        
        # AI聊天标签页 - 暂时隐藏
        # ai_frame = ttk.Frame(self.notebook)
        # self.notebook.add(ai_frame, text="AI 助手")
        # self.ai_tab = AITab(ai_frame)
        
        # 恢复选中的标签页
        if current_tab is not None:
            try:
                self.notebook.select(current_tab)
            except:
                pass
    



def main():
    """主函数"""
    root = tk.Tk()
    app = MainGUI(root)
    root.mainloop()


if __name__ == '__main__':
    # 支持在Windows下使用multiprocessing
    import multiprocessing
    multiprocessing.freeze_support()
    main()

