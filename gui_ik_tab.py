"""
gui_ik_tab.py - IK标签页GUI
实现IK逆运动学批处理功能的GUI界面
参考IK_Pipeline.py的批处理逻辑，确保与convert_c3d.py输出格式衔接
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
import opensim as osim


class IKTab:
    """IK标签页类"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # 存储输入值（必须在create_widgets()之前定义）
        self.model_file = tk.StringVar()
        self.trc_files = []  # 存储多个TRC文件路径
        self.ik_setup_file = tk.StringVar()
        self.output_dir = tk.StringVar()
        
        self.create_widgets()
    
    def create_widgets(self):
        """创建GUI组件"""
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
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(scrollable_frame, text="文件选择", padding="10")
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 缩放后的模型文件
        ttk.Label(file_frame, text="缩放后的模型文件 (.osim):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.model_file, width=60, state='readonly').grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览...", command=self.select_model_file).grid(row=0, column=2, padx=5, pady=5)
        
        # TRC文件列表
        trc_frame = ttk.Frame(file_frame)
        trc_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)
        
        ttk.Label(trc_frame, text="TRC文件列表 (来自convert_c3d.py):").pack(side=tk.LEFT, padx=5)
        ttk.Button(trc_frame, text="添加TRC文件...", command=self.add_trc_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(trc_frame, text="清空列表", command=self.clear_trc_files).pack(side=tk.LEFT, padx=5)
        
        # TRC文件列表框
        listbox_frame = ttk.Frame(file_frame)
        listbox_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W+tk.E+tk.N+tk.S, pady=5)
        
        self.trc_listbox = tk.Listbox(listbox_frame, height=6)
        self.trc_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        trc_scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.trc_listbox.yview)
        self.trc_listbox.configure(yscrollcommand=trc_scrollbar.set)
        trc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # IK设置文件
        ttk.Label(file_frame, text="IK设置XML文件 (只保留marker权重，输入的其他参数会被 GUI 中的设置覆盖):").grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.ik_setup_file, width=60, state='readonly').grid(row=4, column=0, columnspan=2, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览...", command=self.select_ik_setup_file).grid(row=4, column=2, padx=5, pady=5)
        
        # 输出文件夹
        ttk.Label(file_frame, text="输出文件夹:").grid(row=5, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.output_dir, width=60, state='readonly').grid(row=5, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览...", command=self.select_output_dir).grid(row=5, column=2, padx=5, pady=5)
        
        # 运行按钮
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.run_button = ttk.Button(button_frame, text="运行IK批处理", command=self.run_ik, style="Accent.TButton")
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        # 状态显示
        status_frame = ttk.LabelFrame(scrollable_frame, text="状态", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 先创建滚动条
        status_scrollbar = ttk.Scrollbar(status_frame, orient="vertical")
        status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 再创建文本框，并关联滚动条
        self.status_text = tk.Text(status_frame, height=10, wrap=tk.WORD, state='disabled', yscrollcommand=status_scrollbar.set)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置滚动条命令
        status_scrollbar.config(command=self.status_text.yview)
        
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
    
    def select_model_file(self):
        """选择缩放后的模型文件"""
        filename = filedialog.askopenfilename(
            title="选择缩放好的模型文件 (.osim)",
            filetypes=[("OpenSim model", "*.osim")]
        )
        if filename:
            self.model_file.set(filename)
    
    def add_trc_files(self):
        """添加TRC文件到列表"""
        filenames = filedialog.askopenfilenames(
            title="选择一个或多个 TRC 文件（来自convert_c3d.py）",
            filetypes=[("TRC files", "*.trc")]
        )
        for filename in filenames:
            if filename not in self.trc_files:
                self.trc_files.append(filename)
                self.trc_listbox.insert(tk.END, os.path.basename(filename))
    
    def clear_trc_files(self):
        """清空TRC文件列表"""
        self.trc_files.clear()
        self.trc_listbox.delete(0, tk.END)
    
    def select_ik_setup_file(self):
        """选择IK设置XML文件"""
        filename = filedialog.askopenfilename(
            title="选择IK设置XML文件",
            filetypes=[("XML files", "*.xml")]
        )
        if filename:
            self.ik_setup_file.set(filename)
    
    def select_output_dir(self):
        """选择输出文件夹"""
        dirname = filedialog.askdirectory(
            title="选择IK输出文件夹"
        )
        if dirname:
            self.output_dir.set(dirname)
    
    def set_model_file(self, model_path):
        """设置模型文件（用于流水线模式）"""
        if os.path.exists(model_path):
            self.model_file.set(model_path)
    
    def set_trc_folder(self, folder_path):
        """设置TRC文件夹（用于流水线模式，自动添加文件夹中的所有TRC文件）"""
        if os.path.exists(folder_path):
            self.output_dir.set(folder_path)  # 默认输出到TRC文件所在文件夹
            trc_files = list(Path(folder_path).glob("*.trc"))
            for trc_file in trc_files:
                trc_path = str(trc_file)
                if trc_path not in self.trc_files:
                    self.trc_files.append(trc_path)
                    self.trc_listbox.insert(tk.END, trc_file.name)
    
    def log(self, message):
        """在状态文本框中添加日志"""
        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')
        self.parent.update()
    
    def run_ik(self):
        """运行IK批处理"""
        # 验证输入
        if not self.model_file.get():
            messagebox.showerror("错误", "请选择缩放后的模型文件")
            return {'success': False, 'error': '未选择模型文件'}
        
        if not self.trc_files:
            messagebox.showerror("错误", "请至少添加一个TRC文件")
            return {'success': False, 'error': '未选择TRC文件'}
        
        if not self.ik_setup_file.get():
            messagebox.showerror("错误", "请选择IK设置XML文件")
            return {'success': False, 'error': '未选择IK设置文件'}
        
        # 设置输出文件夹（如果未设置，使用第一个TRC文件所在文件夹）
        if not self.output_dir.get():
            output_dir = os.path.dirname(self.trc_files[0])
            self.output_dir.set(output_dir)
        
        output_dir_path = Path(self.output_dir.get())
        output_dir_path.mkdir(parents=True, exist_ok=True)
        
        # 清空状态
        self.status_text.config(state='normal')
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state='disabled')
        
        self.log("=" * 80)
        self.log("开始运行IK批处理...")
        self.log(f"模型文件: {self.model_file.get()}")
        self.log(f"TRC文件数量: {len(self.trc_files)}")
        self.log(f"输出文件夹: {output_dir_path}")
        self.log("=" * 80)
        
        try:
            # 加载模型
            self.log(f"\n加载模型: {os.path.basename(self.model_file.get())}")
            model = osim.Model(str(self.model_file.get()))
            model.initSystem()
            self.log("模型加载成功")
            
            # 批量处理TRC文件
            success_count = 0
            fail_count = 0
            
            for trc_path in self.trc_files:
                trc_file = Path(trc_path)
                self.log(f"\n正在处理: {trc_file.name}")
                
                try:
                    # 创建输出文件名：{trc_stem}_IK.mot
                    output_mot = output_dir_path / f"{trc_file.stem}_IK.mot"
                    
                    # 创建IK工具
                    ik_tool = osim.InverseKinematicsTool(str(self.ik_setup_file.get()))
                    ik_tool.setModel(model)
                    ik_tool.setMarkerDataFileName(str(trc_path))
                    ik_tool.setOutputMotionFileName(str(output_mot))
                    
                    # 设置时间范围
                    marker_data = osim.MarkerData(str(trc_path))
                    ik_tool.setStartTime(marker_data.getStartFrameTime())
                    ik_tool.setEndTime(marker_data.getLastFrameTime())
                    
                    # 运行IK
                    ik_tool.run()
                    
                    self.log(f"✓ IK完成: {output_mot.name}")
                    success_count += 1
                    
                except Exception as e:
                    self.log(f"✗ IK失败: {trc_file.name}")
                    self.log(f"  错误信息: {str(e)}")
                    fail_count += 1
            
            # 总结
            self.log("\n" + "=" * 80)
            self.log("IK批处理完成")
            self.log(f"成功: {success_count} 个文件")
            self.log(f"失败: {fail_count} 个文件")
            self.log("=" * 80)
            
            if fail_count == 0:
                messagebox.showinfo("成功", f"IK批处理完成！\n\n成功处理 {success_count} 个文件\n输出文件夹: {output_dir_path}")
                return {'success': True, 'output_dir': str(output_dir_path), 'success_count': success_count}
            else:
                messagebox.showwarning("部分成功", f"IK批处理完成\n\n成功: {success_count} 个文件\n失败: {fail_count} 个文件")
                return {'success': True, 'output_dir': str(output_dir_path), 'success_count': success_count, 'fail_count': fail_count}
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.log("\n" + "=" * 80)
            self.log("IK批处理出错！")
            self.log(error_msg)
            self.log("=" * 80)
            messagebox.showerror("错误", f"IK批处理出错:\n{str(e)}")
            return {'success': False, 'error': error_msg}

