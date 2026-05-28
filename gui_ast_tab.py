"""
gui_ast_tab.py - AST标签页GUI
实现AST模型缩放功能的GUI界面
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
import opensim as osim
from input_ast import input_ast_gui
from main_ast_v1 import run_ast


class ASTTab:
    """AST标签页类"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # 存储输入值（必须在create_widgets()之前定义）
        self.model_file = tk.StringVar()
        self.trc_file = tk.StringVar()
        self.setup_file = tk.StringVar()
        self.subject_height = tk.StringVar(value="180")
        self.subject_weight = tk.StringVar(value="85")
        self.generic_model_height = tk.StringVar(value="180")
        self.generic_model_weight = tk.StringVar(value="75")
        self.pose = tk.IntVar(value=1)
        self.output_model_name = tk.StringVar(value="ModelScaledMarkerAdj.osim")
        
        # 线程控制
        self.ast_thread = None
        self.stop_requested = False
        
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
        
        # 基础模型文件
        ttk.Label(file_frame, text="基础模型文件 (.osim):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.model_file, width=60, state='readonly').grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览...", command=self.select_model_file).grid(row=0, column=2, padx=5, pady=5)
        
        # 静态TRC文件
        ttk.Label(file_frame, text="静态TRC文件 (.trc):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.trc_file, width=60, state='readonly').grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览...", command=self.select_trc_file).grid(row=1, column=2, padx=5, pady=5)
        
        # 缩放设置XML文件
        ttk.Label(file_frame, text="缩放设置XML文件:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.setup_file, width=60, state='readonly').grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览...", command=self.select_setup_file).grid(row=2, column=2, padx=5, pady=5)
        # 备注说明
        ttk.Label(file_frame, text="备注: 缩放设置XML中受试者身高/质量、原模型文件以及TRC文件路径会被用户当前输入覆盖", 
                  font=('Microsoft YaHei', 8, 'italic'), foreground='#8B008B').grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        # 参数输入区域
        param_frame = ttk.LabelFrame(scrollable_frame, text="参数设置", padding="10")
        param_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 受试者参数
        ttk.Label(param_frame, text="受试者身高 (cm):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(param_frame, textvariable=self.subject_height, width=20).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(param_frame, text="受试者体重 (kg):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(param_frame, textvariable=self.subject_weight, width=20).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 通用模型参数
        ttk.Label(param_frame, text="通用模型身高 (cm):").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(param_frame, textvariable=self.generic_model_height, width=20).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(param_frame, text="通用模型体重 (kg):").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(param_frame, textvariable=self.generic_model_weight, width=20).grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 姿态估计选项
        ttk.Label(param_frame, text="姿态估计:").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Radiobutton(param_frame, text="匹配实验姿势", variable=self.pose, value=1).grid(row=4, column=1, sticky=tk.W, padx=5)
        ttk.Radiobutton(param_frame, text="不匹配实验姿势", variable=self.pose, value=0).grid(row=4, column=2, sticky=tk.W, padx=5)
        
        # 输出设置
        output_frame = ttk.LabelFrame(scrollable_frame, text="输出设置", padding="10")
        output_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(output_frame, text="输出模型文件名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(output_frame, textvariable=self.output_model_name, width=40).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 运行按钮
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.run_button = ttk.Button(button_frame, text="运行AST", command=self.run_ast, style="Accent.TButton")
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="中止", command=self.stop_ast, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
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
        """选择基础模型文件"""
        filename = filedialog.askopenfilename(
            title="选择未缩放的通用基础模型文件",
            filetypes=[('OpenSim模型文件', '*.osim')]
        )
        if filename:
            self.model_file.set(filename)
    
    def select_trc_file(self):
        """选择静态TRC文件"""
        filename = filedialog.askopenfilename(
            title="选择用于缩放的静态试验 TRC 文件",
            filetypes=[('TRC文件', '*.trc')]
        )
        if filename:
            self.trc_file.set(filename)
    
    def select_setup_file(self):
        """选择缩放设置XML文件"""
        filename = filedialog.askopenfilename(
            title="选择用于缩放的 XML 设置文件",
            filetypes=[('XML文件', '*.xml')]
        )
        if filename:
            self.setup_file.set(filename)
    
    def log(self, message):
        """在状态文本框中添加日志，同时输出到后台终端"""
        print(message)  # 输出到后台终端
        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')
        self.parent.update()
    
    def run_ast(self):
        """运行AST缩放流程"""
        # 验证输入
        if not self.model_file.get():
            messagebox.showerror("错误", "请选择基础模型文件")
            return {'success': False, 'error': '未选择基础模型文件'}
        
        if not self.trc_file.get():
            messagebox.showerror("错误", "请选择静态TRC文件")
            return {'success': False, 'error': '未选择静态TRC文件'}
        
        if not self.setup_file.get():
            messagebox.showerror("错误", "请选择缩放设置XML文件")
            return {'success': False, 'error': '未选择缩放设置XML文件'}
        
        try:
            subject_height = float(self.subject_height.get())
            subject_weight = float(self.subject_weight.get())
            generic_model_height = float(self.generic_model_height.get())
            generic_model_weight = float(self.generic_model_weight.get())
        except ValueError:
            messagebox.showerror("错误", "参数必须是数字")
            return {'success': False, 'error': '参数格式错误'}
        
        pose = self.pose.get()
        output_model_name = self.output_model_name.get()
        
        # 清空状态
        self.status_text.config(state='normal')
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state='disabled')
        
        self.log("=" * 80)
        self.log("开始运行AST模型缩放...")
        self.log("=" * 80)
        
        # 禁用运行按钮，启用停止按钮
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 重置停止请求标志
        self.stop_requested = False
        
        # 启动AST运行线程
        import threading
        self.ast_thread = threading.Thread(
            target=self.run_ast_thread,
            args=(subject_height, subject_weight, generic_model_height, generic_model_weight, pose, output_model_name)
        )
        self.ast_thread.daemon = True
        self.ast_thread.start()
    
    def run_ast_thread(self, subject_height, subject_weight, generic_model_height, generic_model_weight, pose, output_model_name):
        """AST运行线程函数"""
        try:
            # 准备输入参数
            inputs = input_ast_gui(
                model_file=self.model_file.get(),
                trc_file=self.trc_file.get(),
                setup_file=self.setup_file.get(),
                subject_height=subject_height,
                subject_weight=subject_weight,
                generic_model_height=generic_model_height,
                generic_model_weight=generic_model_weight,
                pose=pose
            )
            
            # 定义回调函数，用于实时显示每一轮的信息
            def ast_callback(info):
                # 检查是否请求停止
                if self.stop_requested:
                    raise Exception("AST执行已被用户中止")
                # 在主线程中更新GUI
                def update_status():
                    self.log(info['message'])
                self.parent.after(0, update_status)
            
            # 运行AST
            self.log("正在运行AST...")
            result = run_ast(inputs=inputs, output_model_name=output_model_name, callback=ast_callback)
            
            # 检查是否请求停止
            if self.stop_requested:
                # 在主线程中更新GUI
                def update_gui_stopped():
                    self.log("\n" + "=" * 80)
                    self.log("AST运行已被中止！")
                    self.log("=" * 80)
                    # 恢复按钮状态
                    self.run_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                # 在主线程中执行GUI更新
                self.parent.after(0, update_gui_stopped)
                return {'success': False, 'error': 'AST执行已被用户中止'}
            
            # 在主线程中更新GUI
            def update_gui():
                if result['success']:
                    self.log("\n" + "=" * 80)
                    self.log("AST运行成功！")
                    self.log(f"输出模型: {result['output_model_path']}")
                    self.log("=" * 80)
                    messagebox.showinfo("成功", f"AST运行成功！\n\n输出模型:\n{result['output_model_path']}")
                else:
                    self.log("\n" + "=" * 80)
                    self.log("AST运行失败！")
                    self.log(f"错误: {result.get('error', '未知错误')}")
                    self.log("=" * 80)
                    messagebox.showerror("错误", f"AST运行失败:\n{result.get('error', '未知错误')}")
                # 恢复按钮状态
                self.run_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
            
            # 在主线程中执行GUI更新
            self.parent.after(0, update_gui)
            
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            
            # 检查是否是用户中止
            if "AST执行已被用户中止" in str(e):
                # 在主线程中更新GUI
                def update_gui_stopped():
                    self.log("\n" + "=" * 80)
                    self.log("AST运行已被中止！")
                    self.log("=" * 80)
                    # 恢复按钮状态
                    self.run_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                # 在主线程中执行GUI更新
                self.parent.after(0, update_gui_stopped)
                return {'success': False, 'error': 'AST执行已被用户中止'}
            else:
                # 在主线程中更新GUI
                def update_gui_error():
                    self.log("\n" + "=" * 80)
                    self.log("AST运行出错！")
                    self.log(error_msg)
                    self.log("=" * 80)
                    messagebox.showerror("错误", f"AST运行出错:\n{str(e)}")
                    # 恢复按钮状态
                    self.run_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                # 在主线程中执行GUI更新
                self.parent.after(0, update_gui_error)
                return {'success': False, 'error': error_msg}
    
    def stop_ast(self):
        """中止AST执行"""
        self.log("正在中止AST执行...")
        self.stop_requested = True
        
        # 恢复按钮状态
        def enable_buttons():
            self.run_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
        self.parent.after(1000, enable_buttons)

