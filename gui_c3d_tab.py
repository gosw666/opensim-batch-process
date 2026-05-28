"""
C3D转换标签页模块
用于将C3D文件转换为TRC和MOT格式
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import traceback

from convert_c3d import convert_c3d_to_trc_and_mot


class C3DTab:
    """C3D转换标签页类"""
    
    def __init__(self, parent):
        self.parent = parent
        self.create_widgets()
        
        # 存储选择的文件列表
        self.selected_files = []
    
    def create_widgets(self):
        """创建C3D转换标签页的GUI组件"""
        # 创建滚动框架
        canvas = tk.Canvas(self.parent, bg='#FFE4E1')  # 粉色背景
        scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 标题
        title_label = ttk.Label(
            scrollable_frame, 
            text="C3D 文件转换", 
            font=('Microsoft YaHei', 12, 'bold')
        )
        title_label.pack(pady=5)
        
        # 功能说明
        desc_label = ttk.Label(
            scrollable_frame, 
            text="将C3D文件转换为TRC（标记点）和MOT（力板数据）格式",
            font=('Microsoft YaHei', 10)
        )
        desc_label.pack(pady=5)
        
        # 单位转换说明
        units_frame = ttk.LabelFrame(scrollable_frame, text="单位转换说明", padding="10")
        units_frame.pack(fill=tk.X, pady=5)
        
        units_text = """
单位转换规则：
1. 标记点数据：mm → m（除以1000）
2. 力板数据：
   - 位置：mm → m（除以1000）
   - 力矩：N·mm → N·m（除以1000）
   - 力：保持不变（N）

坐标系统转换：
- 输入（Vicon）：X=右, Y=前, Z=上
- 输出（OpenSim）：X=前, Y=上, Z=右
- 转换规则：X_new=Y_old, Y_new=Z_old, Z_new=X_old
        """
        units_label = ttk.Label(
            units_frame, 
            text=units_text,
            font=('Microsoft YaHei', 9),
            justify=tk.LEFT
        )
        units_label.pack(fill=tk.X)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(scrollable_frame, text="文件选择", padding="10")
        file_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 文件选择按钮
        button_frame = ttk.Frame(file_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.select_files_btn = ttk.Button(
            button_frame, 
            text="选择C3D文件", 
            command=self.select_c3d_files
        )
        self.select_files_btn.pack(side=tk.LEFT, padx=5)
        
        self.select_folder_btn = ttk.Button(
            button_frame, 
            text="选择文件夹", 
            command=self.select_folder
        )
        self.select_folder_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_files_btn = ttk.Button(
            button_frame, 
            text="清空列表", 
            command=self.clear_file_list
        )
        self.clear_files_btn.pack(side=tk.RIGHT, padx=5)
        
        # 文件列表
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 滚动条
        scrollbar_list = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar_list.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 文件列表框
        self.file_listbox = tk.Listbox(
            list_frame, 
            yscrollcommand=scrollbar_list.set,
            height=10,
            font=('Microsoft YaHei', 9)
        )
        self.file_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar_list.config(command=self.file_listbox.yview)
        
        # 输出目录设置
        output_frame = ttk.LabelFrame(scrollable_frame, text="输出设置", padding="10")
        output_frame.pack(fill=tk.X, pady=5)
        
        # 输出目录标签
        ttk.Label(output_frame, text="输出目录：").pack(side=tk.LEFT, padx=5)
        
        # 输入框和浏览按钮
        entry_frame = ttk.Frame(output_frame)
        entry_frame.pack(fill=tk.X, expand=True, padx=5)
        
        self.output_dir_var = tk.StringVar()
        self.output_dir_entry = ttk.Entry(
            entry_frame, 
            textvariable=self.output_dir_var,
            width=50
        )
        self.output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.browse_output_btn = ttk.Button(
            entry_frame, 
            text="浏览", 
            command=self.browse_output_dir
        )
        self.browse_output_btn.pack(side=tk.LEFT, padx=5)
        
        # 备注说明（换行显示）
        ttk.Label(output_frame, text="备注: 转换后会在输出目录下自动创建 'trc' 和 'mot' 子文件夹保存对应文件", 
                  font=('Microsoft YaHei', 8, 'italic'), foreground='#8B008B').pack(anchor=tk.W, pady=2)
        
        # 转换按钮
        self.convert_btn = ttk.Button(
            scrollable_frame, 
            text="开始转换", 
            command=self.start_conversion,
            style='TButton'
        )
        self.convert_btn.pack(pady=10)
        
        # 状态显示
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(
            scrollable_frame, 
            textvariable=self.status_var,
            font=('Microsoft YaHei', 10)
        )
        self.status_label.pack(pady=5)
        
        # 日志输出
        log_frame = ttk.LabelFrame(scrollable_frame, text="转换日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            log_frame, 
            yscrollcommand=log_scrollbar.set,
            height=10,
            font=('Courier New', 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=self.log_text.yview)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定窗口大小变化事件，调整Canvas大小
        self.parent.bind('<Configure>', lambda e: canvas.configure(width=e.width-20))
        
        # 绑定鼠标滚轮事件，实现滚动功能
        def on_mouse_wheel(event):
            # 计算滚动量
            scroll_amount = int(-1*(event.delta/120))
            # 执行滚动
            canvas.yview_scroll(scroll_amount, "units")
        
        # 绑定到canvas和scrollable_frame，确保在整个滚动区域都能响应
        canvas.bind("<MouseWheel>", on_mouse_wheel)
        scrollable_frame.bind("<MouseWheel>", on_mouse_wheel)
        
        # 为scrollable_frame中的所有子组件绑定鼠标滚轮事件
        def bind_to_children(widget):
            widget.bind("<MouseWheel>", on_mouse_wheel)
            for child in widget.winfo_children():
                bind_to_children(child)
        
        # 递归绑定到所有子组件
        bind_to_children(scrollable_frame)
    
    def select_c3d_files(self):
        """选择C3D文件"""
        files = filedialog.askopenfilenames(
            title="选择C3D文件",
            filetypes=[("C3D文件", "*.c3d"), ("所有文件", "*")]
        )
        
        if files:
            for file in files:
                if file not in self.selected_files:
                    self.selected_files.append(file)
                    self.file_listbox.insert(tk.END, file)
            self.status_var.set(f"已选择 {len(self.selected_files)} 个文件")
    
    def select_folder(self):
        """选择包含C3D文件的文件夹"""
        folder = filedialog.askdirectory(title="选择文件夹")
        
        if folder:
            c3d_files = [os.path.join(folder, f) for f in os.listdir(folder) 
                        if f.lower().endswith('.c3d')]
            
            if c3d_files:
                for file in c3d_files:
                    if file not in self.selected_files:
                        self.selected_files.append(file)
                        self.file_listbox.insert(tk.END, file)
                self.status_var.set(f"已选择 {len(self.selected_files)} 个文件")
            else:
                messagebox.showinfo("提示", "所选文件夹中没有C3D文件")
    
    def clear_file_list(self):
        """清空文件列表"""
        self.selected_files = []
        self.file_listbox.delete(0, tk.END)
        self.status_var.set("就绪")
    
    def browse_output_dir(self):
        """浏览输出目录"""
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.output_dir_var.set(dir_path)
    
    def start_conversion(self):
        """开始转换"""
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择C3D文件")
            return
        
        # 获取输出目录
        output_dir = self.output_dir_var.get()
        if not output_dir:
            output_dir = None  # 使用默认目录（C3D文件所在目录）
        
        # 禁用按钮
        self.convert_btn.config(state=tk.DISABLED)
        self.select_files_btn.config(state=tk.DISABLED)
        self.select_folder_btn.config(state=tk.DISABLED)
        self.clear_files_btn.config(state=tk.DISABLED)
        self.browse_output_btn.config(state=tk.DISABLED)
        
        # 清空日志
        self.log_text.delete(1.0, tk.END)
        
        # 启动转换线程
        conversion_thread = threading.Thread(
            target=self.convert_files, 
            args=(output_dir,)
        )
        conversion_thread.daemon = True
        conversion_thread.start()
    
    def convert_files(self, output_dir):
        """转换文件的线程函数"""
        self.status_var.set("转换中...")
        
        success_count = 0
        error_count = 0
        
        for i, c3d_file in enumerate(self.selected_files, 1):
            try:
                self.log_text.insert(tk.END, f"\n处理文件 {i}/{len(self.selected_files)}: {os.path.basename(c3d_file)}")
                self.log_text.see(tk.END)
                
                # 执行转换
                trc_path, mot_path = convert_c3d_to_trc_and_mot(c3d_file, output_dir)
                
                # 记录结果
                self.log_text.insert(tk.END, f"\n✓ 转换完成")
                if trc_path:
                    self.log_text.insert(tk.END, f"\n  TRC: {os.path.basename(trc_path)}")
                if mot_path:
                    self.log_text.insert(tk.END, f"\n  MOT: {os.path.basename(mot_path)}")
                
                success_count += 1
                
            except Exception as e:
                self.log_text.insert(tk.END, f"\n✗ 转换失败: {str(e)}")
                self.log_text.insert(tk.END, f"\n  错误信息: {traceback.format_exc()}")
                error_count += 1
            
            self.log_text.see(tk.END)
        
        # 恢复按钮状态
        self.convert_btn.config(state=tk.NORMAL)
        self.select_files_btn.config(state=tk.NORMAL)
        self.select_folder_btn.config(state=tk.NORMAL)
        self.clear_files_btn.config(state=tk.NORMAL)
        self.browse_output_btn.config(state=tk.NORMAL)
        
        # 显示转换结果
        self.status_var.set(f"转换完成: {success_count} 成功, {error_count} 失败")
        
        if success_count > 0:
            messagebox.showinfo("成功", f"转换完成！\n成功: {success_count} 个文件\n失败: {error_count} 个文件")
        else:
            messagebox.showerror("错误", f"转换失败！\n所有文件都转换失败，请检查错误信息")
