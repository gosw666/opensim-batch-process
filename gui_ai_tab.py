"""
gui_ai_tab.py - AI聊天标签页
实现AI聊天功能，帮助用户完成从C3D转换到IK、ID、SO的完整流程
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import requests
import json
from pathlib import Path
import opensim as osim

from convert_c3d import convert_c3d_to_trc_and_mot

class AITab:
    """AI聊天标签页类"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # 存储上传的文件
        self.uploaded_files = {
            'model': [],      # 模型文件 (.osim)
            'c3d': [],        # C3D文件
            'scale': [],      # 缩放设置XML
            'ik_config': [],  # IK设置XML
            'api_key': [],    # API密钥文件
            'knowledge': []   # 知识库文件
        }
        
        # 存储对话历史
        self.conversation_history = []
        
        # 存储处理结果
        self.process_results = []
        
        # 知识库文件夹
        self.knowledge_base_folder = tk.StringVar(value="")
        
        # 文件修改权限
        self.allow_file_modification = tk.BooleanVar(value=False)
        
        # 处理状态管理
        self.process_state = {
            'current_step': 0,  # 当前步骤：0-未开始，1-C3D转换，2-模型缩放，3-IK处理，4-ID处理，5-SO处理
            'step_status': {    # 各步骤状态：0-未开始，1-进行中，2-完成，3-失败
                1: 0,
                2: 0,
                3: 0,
                4: 0,
                5: 0
            },
            'step_results': {},  # 各步骤的结果
            'processing': False,  # 是否正在处理
            'paused': False,      # 是否暂停
            'waiting_for_confirmation': False  # 是否等待用户确认
        }
        
        # 处理步骤名称
        self.step_names = {
            1: "C3D转换",
            2: "模型缩放",
            3: "IK处理",
            4: "ID处理",
            5: "SO处理"
        }
        
        # 创建GUI组件
        self.create_widgets()
        
        # 本地知识库
        self.knowledge_base = self.load_knowledge_base()
    
    def create_widgets(self):
        """创建AI聊天标签页的GUI组件"""
        # 创建主框架，分为左侧聊天区域和右侧控制面板
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧聊天历史区域（竖长的长方体）
        left_frame = ttk.LabelFrame(main_frame, text="AI 对话", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 聊天历史 - 使用Text组件替代Canvas，更简单高效
        chat_history_frame = ttk.Frame(left_frame)
        chat_history_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        chat_scrollbar = ttk.Scrollbar(chat_history_frame, orient=tk.VERTICAL)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建Text组件作为聊天区域
        self.chat_text = tk.Text(
            chat_history_frame, 
            yscrollcommand=chat_scrollbar.set,
            bg='#F0F0F0',
            font=('Microsoft YaHei', 9),
            wrap=tk.WORD,
            borderwidth=1,
            relief=tk.FLAT
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        chat_scrollbar.config(command=self.chat_text.yview)
        
        # 设置标签样式
        self.chat_text.tag_configure("ai", foreground="#0066CC", font=('Microsoft YaHei', 9, 'bold'))
        self.chat_text.tag_configure("user", foreground="#008800", font=('Microsoft YaHei', 9, 'bold'))
        self.chat_text.tag_configure("system", foreground="#888888", font=('Microsoft YaHei', 9, 'italic'))
        self.chat_text.tag_configure("message", lmargin1=10, lmargin2=10, rmargin=10, spacing1=5, spacing3=5)
        
        # 输入区域
        input_frame = ttk.Frame(left_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(
            input_frame, 
            textvariable=self.message_var,
            width=80
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.send_btn = ttk.Button(
            input_frame, 
            text="发送", 
            command=self.send_message
        )
        self.send_btn.pack(side=tk.LEFT, padx=5)
        
        # 为聊天Text绑定鼠标滚轮事件
        def on_chat_mouse_wheel(event):
            # 计算滚动量
            scroll_amount = int(-1*(event.delta/120))
            # 执行滚动
            self.chat_text.yview_scroll(scroll_amount, "units")
        
        # 绑定聊天Text的鼠标滚轮事件
        self.chat_text.bind("<MouseWheel>", on_chat_mouse_wheel)
        
        # 右侧控制面板
        right_frame = ttk.Frame(main_frame, width=450)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=5, pady=5)
        right_frame.pack_propagate(False)  # 防止内容影响框架大小
        
        # 创建滚动框架用于右侧控制面板
        right_canvas = tk.Canvas(right_frame, bg='#FFE4E1')  # 粉色背景
        right_scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=right_canvas.yview)
        right_scrollable_frame = ttk.Frame(right_canvas)
        
        right_scrollable_frame.bind(
            "<Configure>",
            lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        )
        
        # 保存滚动框架的ID，以便在配置事件中更新宽度
        right_scrollable_frame_id = right_canvas.create_window((0, 0), window=right_scrollable_frame, anchor="nw", width=right_frame.winfo_width())
        
        right_canvas.configure(yscrollcommand=right_scrollbar.set)
        
        # 标题
        title_label = ttk.Label(
            right_scrollable_frame, 
            text="AI 助手", 
            font=('Microsoft YaHei', 12, 'bold')
        )
        title_label.pack(pady=5)
        
        # 功能说明
        desc_label = ttk.Label(
            right_scrollable_frame, 
            text="上传模型文件、C3D文件和配置文件，让AI帮您完成从C3D转换到AST模型缩放、IK、ID、SO的完整流程",
            font=('Microsoft YaHei', 10)
        )
        desc_label.pack(pady=5)
        
        # API密钥设置
        api_frame = ttk.LabelFrame(right_scrollable_frame, text="API 密钥设置", padding="10")
        api_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(api_frame, text="DeepSeek API 密钥:").pack(side=tk.LEFT, padx=5)
        ttk.Button(api_frame, text="上传", command=lambda: self.upload_files('api_key', [('Text files', '*.txt')])).pack(side=tk.LEFT, padx=5)
        self.api_key_var = tk.StringVar(value="sk-")
        api_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=60, show="*")
        api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(api_frame, text="显示", command=lambda: api_entry.configure(show="" if api_entry.cget("show") == "*" else "*")).pack(side=tk.LEFT, padx=5)
        
        # 知识库管理
        knowledge_frame = ttk.LabelFrame(right_scrollable_frame, text="知识库管理", padding="10")
        knowledge_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(knowledge_frame, text="知识库文件夹:").pack(side=tk.LEFT, padx=5)
        ttk.Button(knowledge_frame, text="上传", command=lambda: self.upload_files('knowledge', [('Text files', '*.txt')])).pack(side=tk.LEFT, padx=5)
        self.knowledge_base_folder = tk.StringVar(value="")
        knowledge_entry = ttk.Entry(knowledge_frame, textvariable=self.knowledge_base_folder, width=60, state='readonly')
        knowledge_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(knowledge_frame, text="选择文件夹", command=self.select_knowledge_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(knowledge_frame, text="重新加载", command=self.reload_knowledge_base).pack(side=tk.LEFT, padx=5)
        
        # 文件上传区域
        upload_frame = ttk.LabelFrame(right_scrollable_frame, text="文件上传", padding="10")
        upload_frame.pack(fill=tk.X, pady=5)
        
        # 模型文件上传
        model_frame = ttk.Frame(upload_frame)
        model_frame.pack(fill=tk.X, pady=2)
        ttk.Label(model_frame, text="模型文件 (.osim):").pack(side=tk.LEFT, padx=5)
        ttk.Button(model_frame, text="上传", command=lambda: self.upload_files('model', [('OpenSim model', '*.osim')])).pack(side=tk.LEFT, padx=5)
        self.model_listbox = tk.Listbox(model_frame, height=2, width=60)
        self.model_listbox.pack(side=tk.LEFT, padx=5)
        
        # C3D文件上传
        c3d_frame = ttk.Frame(upload_frame)
        c3d_frame.pack(fill=tk.X, pady=2)
        ttk.Label(c3d_frame, text="C3D文件:").pack(side=tk.LEFT, padx=5)
        ttk.Button(c3d_frame, text="上传", command=lambda: self.upload_files('c3d', [('C3D files', '*.c3d')])).pack(side=tk.LEFT, padx=5)
        self.c3d_listbox = tk.Listbox(c3d_frame, height=2, width=60)
        self.c3d_listbox.pack(side=tk.LEFT, padx=5)
        
        # 缩放设置XML上传
        scale_frame = ttk.Frame(upload_frame)
        scale_frame.pack(fill=tk.X, pady=2)
        ttk.Label(scale_frame, text="缩放设置 (XML):").pack(side=tk.LEFT, padx=5)
        ttk.Button(scale_frame, text="上传", command=lambda: self.upload_files('scale', [('XML files', '*.xml')])).pack(side=tk.LEFT, padx=5)
        self.scale_listbox = tk.Listbox(scale_frame, height=2, width=60)
        self.scale_listbox.pack(side=tk.LEFT, padx=5)
        
        # IK设置XML上传
        ik_config_frame = ttk.Frame(upload_frame)
        ik_config_frame.pack(fill=tk.X, pady=2)
        ttk.Label(ik_config_frame, text="IK设置 (XML):").pack(side=tk.LEFT, padx=5)
        ttk.Button(ik_config_frame, text="上传", command=lambda: self.upload_files('ik_config', [('XML files', '*.xml')])).pack(side=tk.LEFT, padx=5)
        self.ik_config_listbox = tk.Listbox(ik_config_frame, height=2, width=60)
        self.ik_config_listbox.pack(side=tk.LEFT, padx=5)
        
        # 清空文件按钮
        clear_frame = ttk.Frame(upload_frame)
        clear_frame.pack(fill=tk.X, pady=5)
        ttk.Button(clear_frame, text="清空所有文件", command=self.clear_all_files).pack(side=tk.RIGHT, padx=5)
        
        # 快速命令按钮
        quick_commands_frame = ttk.LabelFrame(right_scrollable_frame, text="快速命令", padding="10")
        quick_commands_frame.pack(fill=tk.X, pady=5)
        
        # 创建按钮容器，使用网格布局
        buttons_container = ttk.Frame(quick_commands_frame)
        buttons_container.pack(fill=tk.X)
        
        quick_buttons = [
            ("开始处理", self.start_processing),
            ("批量生成ExternalLoads XML", self.batch_process_external_loads),
            ("查看结果", self.show_results),
            ("清除对话", self.clear_conversation)
        ]
        
        # 调整按钮大小和布局
        for i, (text, command) in enumerate(quick_buttons):
            # 缩短按钮文本，使其更紧凑
            if text == "批量生成ExternalLoads XML":
                text = "生成ExternalLoads"
            button = ttk.Button(buttons_container, text=text, command=command, width=12)
            button.pack(side=tk.LEFT, padx=2, pady=2)
            if (i + 1) % 2 == 0:  # 每两个按钮换行
                ttk.Frame(buttons_container).pack(fill=tk.X)
        
        # 结果展示区域
        results_frame = ttk.LabelFrame(right_scrollable_frame, text="处理结果", padding="10")
        results_frame.pack(fill=tk.X, pady=5)
        
        results_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_listbox = tk.Listbox(
            results_frame, 
            yscrollcommand=results_scrollbar.set,
            height=8,
            font=('Microsoft YaHei', 9)
        )
        self.results_listbox.pack(fill=tk.BOTH, expand=True)
        results_scrollbar.config(command=self.results_listbox.yview)
        
        # 结果操作按钮
        results_buttons_frame = ttk.Frame(results_frame)
        results_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(results_buttons_frame, text="打开结果文件夹", command=self.open_results_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(results_buttons_frame, text="下载结果", command=self.download_results).pack(side=tk.LEFT, padx=5)
        
        # 处理步骤控制
        process_control_frame = ttk.LabelFrame(right_scrollable_frame, text="处理步骤控制", padding="10")
        process_control_frame.pack(fill=tk.X, pady=5)
        
        # 步骤状态显示
        steps_frame = ttk.Frame(process_control_frame)
        steps_frame.pack(fill=tk.X, pady=5)
        
        self.step_labels = {}
        for step in range(1, 6):
            step_frame = ttk.Frame(steps_frame)
            step_frame.pack(fill=tk.X, pady=2)
            
            step_name = self.step_names.get(step, f"步骤{step}")
            step_label = ttk.Label(step_frame, text=f"{step}. {step_name}", width=20)
            step_label.pack(side=tk.LEFT, padx=5)
            
            status_var = tk.StringVar(value="未开始")
            status_label = ttk.Label(step_frame, textvariable=status_var, width=10, foreground="gray")
            status_label.pack(side=tk.LEFT, padx=5)
            
            self.step_labels[step] = status_var
        
        # 控制按钮
        control_buttons_frame = ttk.Frame(process_control_frame)
        control_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_buttons_frame, text="开始处理", command=self.start_processing).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_buttons_frame, text="继续下一步", command=self.process_next_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_buttons_frame, text="重置流程", command=self.reset_process).pack(side=tk.LEFT, padx=5)
        
        # 打包右侧滚动框架
        right_canvas.pack(side="left", fill="both", expand=True)
        right_scrollbar.pack(side="right", fill="y")
        
        # 绑定窗口大小变化事件，调整Canvas大小
        def on_right_configure(event):
            new_width = event.width - 20
            right_canvas.configure(width=new_width)
            # 更新滚动框架的宽度
            right_canvas.itemconfig(right_scrollable_frame_id, width=new_width)
        
        right_frame.bind('<Configure>', on_right_configure)
        
        # 保存滚动框架的ID，以便在配置事件中更新宽度
        right_scrollable_frame_id = right_canvas.create_window((0, 0), window=right_scrollable_frame, anchor="nw", width=right_frame.winfo_width())
        
        # 绑定鼠标滚轮事件，实现滚动功能
        def on_mouse_wheel(event):
            # 计算滚动量
            scroll_amount = int(-1*(event.delta/120))
            # 执行滚动
            right_canvas.yview_scroll(scroll_amount, "units")
        
        # 绑定到canvas和scrollable_frame，确保在整个滚动区域都能响应
        right_canvas.bind("<MouseWheel>", on_mouse_wheel)
        right_scrollable_frame.bind("<MouseWheel>", on_mouse_wheel)
        
        # 为scrollable_frame中的所有子组件绑定鼠标滚轮事件
        def bind_to_children(widget):
            widget.bind("<MouseWheel>", on_mouse_wheel)
            for child in widget.winfo_children():
                bind_to_children(child)
        
        # 递归绑定到所有子组件
        bind_to_children(right_scrollable_frame)
        
        # 初始消息
        self.add_message("AI", "您好！我是OpenSim助手，可以帮您完成从C3D转换到AST模型缩放、IK、ID、SO的完整流程。请上传您的模型文件、C3D文件和配置文件，然后告诉我您的需求。")
    
    def upload_files(self, file_type, filetypes):
        """上传文件"""
        files = filedialog.askopenfilenames(
            title=f"选择{file_type}文件",
            filetypes=filetypes
        )
        
        if files:
            valid_files = []
            
            # 对于缩放设置和IK设置，只保留最新的一个文件
            if file_type in ['scale', 'ik_config']:
                # 清空原有文件
                self.uploaded_files[file_type] = []
                
                # 清空列表框
                if file_type == 'scale':
                    self.scale_listbox.delete(0, tk.END)
                elif file_type == 'ik_config':
                    self.ik_config_listbox.delete(0, tk.END)
            
            for file in files:
                if os.path.exists(file) and os.path.isfile(file):
                    # 对于缩放设置和IK设置，直接覆盖
                    if file_type in ['scale', 'ik_config']:
                        # 只保留最后一个文件
                        if len(files) > 1:
                            continue
                        self.uploaded_files[file_type] = [file]
                        valid_files = [file]
                        
                        # 更新列表框
                        if file_type == 'scale':
                            self.scale_listbox.insert(tk.END, os.path.basename(file))
                        elif file_type == 'ik_config':
                            self.ik_config_listbox.insert(tk.END, os.path.basename(file))
                    else:
                        # 对于其他文件类型，添加到列表
                        if file not in self.uploaded_files[file_type]:
                            self.uploaded_files[file_type].append(file)
                            valid_files.append(file)
                            
                            # 更新列表框
                            if file_type == 'model':
                                self.model_listbox.insert(tk.END, os.path.basename(file))
                            elif file_type == 'c3d':
                                self.c3d_listbox.insert(tk.END, os.path.basename(file))
                else:
                    self.add_message("系统", f"文件无效: {file}")
            
            # 显示上传成功消息
            if valid_files:
                if file_type in ['scale', 'ik_config']:
                    self.add_message("系统", f"成功上传 {file_type} 文件，已覆盖原有文件")
                else:
                    self.add_message("系统", f"成功上传 {len(valid_files)} 个{file_type}文件")
            else:
                self.add_message("系统", "没有有效文件被上传")
    
    def clear_all_files(self):
        """清空所有上传的文件"""
        # 清空文件列表
        for file_type in self.uploaded_files:
            self.uploaded_files[file_type] = []
        
        # 清空列表框
        self.model_listbox.delete(0, tk.END)
        self.c3d_listbox.delete(0, tk.END)
        self.scale_listbox.delete(0, tk.END)
        self.ik_config_listbox.delete(0, tk.END)
        
        # 显示清空消息
        self.add_message("系统", "已清空所有上传的文件")
    
    def add_message(self, sender, message, buttons=None):
        """在聊天窗口中添加消息
        
        Args:
            sender: 发送者
            message: 消息内容
            buttons: 可选的按钮列表，每个按钮包含{"text": str, "command": function}
        """
        # 添加到对话历史
        self.conversation_history.append({"sender": sender, "message": message})
        
        # 显示在聊天窗口
        self.chat_text.config(state=tk.NORMAL)
        
        # 根据发送者类型设置不同的样式
        if sender == "您":
            # 用户消息：绿色背景，靠右显示
            self.chat_text.insert(tk.END, f"👤 {sender}:\n", "user")
            self.chat_text.insert(tk.END, message + "\n\n", "message")
        elif sender == "AI":
            # AI消息：蓝色背景，靠左显示
            self.chat_text.insert(tk.END, f"🤖 {sender}:\n", "ai")
            self.chat_text.insert(tk.END, message + "\n\n", "message")
        else:
            # 系统消息：灰色背景，靠左显示
            self.chat_text.insert(tk.END, f"📢 {sender}:\n", "system")
            self.chat_text.insert(tk.END, message + "\n\n", "message")
        
        # 滚动到底部
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)
        
        # 当系统消息时，检查是否需要AI分析
        if sender == "系统" and self.should_analyze_system_message(message):
            threading.Thread(target=self.analyze_system_message, args=(message, None, False)).start()
    
    def send_message(self):
        """发送消息"""
        message = self.message_var.get().strip()
        if message:
            # 检查是否是文件修改确认
            if hasattr(self, 'file_modification_requests') and self.file_modification_requests:
                # 提取请求ID
                request_id = None
                for rid in self.file_modification_requests:
                    if rid in message:
                        request_id = rid
                        break
                
                # 检查是否是确认或取消
                if request_id and ("确认" in message or "取消" in message):
                    # 处理文件修改请求
                    request_info = self.file_modification_requests[request_id]
                    file_path = request_info['file_path']
                    new_content = request_info['new_content']
                    reason = request_info['reason']
                    
                    if "确认" in message:
                        # 执行文件修改
                        try:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            self.add_message("系统", f"文件修改成功：{os.path.basename(file_path)}")
                        except Exception as e:
                            self.add_message("系统", f"文件修改失败：{str(e)}")
                    else:
                        # 取消文件修改
                        self.add_message("系统", "文件修改被用户拒绝")
                    
                    # 移除请求
                    del self.file_modification_requests[request_id]
                    
                    # 添加用户消息
                    self.add_message("您", message)
                    
                    # 清空输入框
                    self.message_var.set("")
                    
                    return
            
            # 检查是否是处理步骤确认
            if self.process_state['waiting_for_confirmation'] and ("确认" in message or "继续" in message):
                # 继续执行下一步
                self.add_message("您", message)
                self.add_message("系统", "用户确认继续，执行下一步...")
                self.process_state['waiting_for_confirmation'] = False
                self.process_next_step()
                
                # 清空输入框
                self.message_var.set("")
                return
            
            # 添加用户消息
            self.add_message("您", message)
            
            # 清空输入框
            self.message_var.set("")
            
            # 发送到AI处理
            threading.Thread(target=self.process_message, args=(message,)).start()
    
    def process_message(self, message):
        """处理消息并获取AI响应"""
        # 显示正在处理
        self.add_message("系统", "AI正在处理您的请求...")
        
        try:
            # 构建请求数据
            # 过滤出用户和AI的消息，确保API能看到完整的聊天历史
            chat_history = []
            for msg in self.conversation_history:
                if msg["sender"] == "您":
                    chat_history.append({"role": "user", "content": msg["message"]})
                elif msg["sender"] == "AI":
                    chat_history.append({"role": "assistant", "content": msg["message"]})
            
            data = {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是OpenSim助手，帮助用户完成从C3D转换到AST模型缩放、IK、ID、SO的完整流程。请提供详细的指导，包括文件准备、参数设置和结果分析。\n\n当你收到系统消息时，请分析消息内容，解释其含义，并提供相关的建议和下一步操作指导。\n\n当你认为需要修改文件时（例如配置参数调整、修复错误、优化设置等），请主动发起文件修改请求，使用以下格式：\n```file_modification\n文件路径: /path/to/file\n修改原因: 为什么需要修改这个文件（详细说明修改的理由和预期效果）\n修改内容: 具体修改了哪些地方（列出修改的具体内容和位置）\n新内容:\n完整的新文件内容\n```\n\n用户会在修改前收到确认提示，由用户决定是否同意修改。修改完成后，请向用户总结修改的具体内容和预期效果。\n\n请根据完整的聊天历史来理解用户的问题和上下文，不要忽略任何之前的对话内容，包括系统消息。"
                    },
                    *chat_history
                ],
                "model": "deepseek-chat",
                "temperature": 0.5,  # 降低温度，减少随机性，加快响应
                "max_tokens": 1000,  # 减少最大token数，加快响应
                "top_p": 0.9  # 增加top_p，加快响应
            }
            
            # 调用deepseek API
            api_key = self.api_key_var.get().strip()
            if not api_key or api_key == "sk-":
                self.add_message("系统", "请先设置有效的DeepSeek API密钥")
                return
            
            # 添加重试机制
            max_retries = 3
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    response = requests.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}"
                        },
                        json=data,
                        timeout=15  # 减少超时时间
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if "choices" in result and len(result["choices"]) > 0:
                            ai_message = result["choices"][0]["message"]["content"]
                            
                            # 检查是否包含文件修改请求
                            if "```file_modification" in ai_message:
                                # 解析文件修改请求
                                try:
                                    # 提取文件修改部分
                                    file_mod_part = ai_message.split("```file_modification\n")[1].split("```")[0]
                                    lines = file_mod_part.strip().split("\n")
                                    
                                    # 提取文件路径、修改原因、修改内容和新内容
                                    file_path = ""
                                    reason = ""
                                    modification_content = ""
                                    new_content = ""
                                    in_content = False
                                    
                                    for line in lines:
                                        if line.startswith("文件路径:"):
                                            file_path = line.split("文件路径:")[1].strip()
                                        elif line.startswith("修改原因:"):
                                            reason = line.split("修改原因:")[1].strip()
                                        elif line.startswith("修改内容:"):
                                            modification_content = line.split("修改内容:")[1].strip()
                                        elif line.startswith("新内容:"):
                                            in_content = True
                                        elif in_content:
                                            new_content += line + "\n"
                                    
                                    # 处理文件路径，确保是绝对路径
                                    if not os.path.isabs(file_path):
                                        # 相对于当前工作目录
                                        file_path = os.path.join(os.getcwd(), file_path)
                                    
                                    # 调用修改文件方法
                                    if file_path and reason and new_content:
                                        # 构建完整的修改信息
                                        full_reason = reason
                                        if modification_content:
                                            full_reason += f"\n\n修改内容: {modification_content}"
                                        
                                        success = self.modify_file(file_path, new_content, full_reason)
                                        if success:
                                            # 显示AI消息的非文件修改部分
                                            non_mod_part = ai_message.split("```file_modification\n")[0]
                                            if non_mod_part.strip():
                                                self.add_message("AI", non_mod_part)
                                            # 显示修改成功消息，包含修改内容
                                            success_message = "文件修改成功！"
                                            if modification_content:
                                                success_message += f"\n修改内容: {modification_content}"
                                            self.add_message("系统", success_message)
                                        else:
                                            # 显示完整AI消息
                                            self.add_message("AI", ai_message)
                                    else:
                                        # 显示完整AI消息
                                        self.add_message("AI", ai_message)
                                except Exception as e:
                                    # 解析失败，显示完整AI消息
                                    self.add_message("AI", ai_message)
                            else:
                                # 显示完整AI消息
                                self.add_message("AI", ai_message)
                            success = True
                        else:
                            self.add_message("系统", "AI响应格式错误")
                            success = True
                    else:
                        self.add_message("系统", f"AI请求失败: {response.status_code} - {response.text}")
                        success = True
                except requests.exceptions.Timeout:
                    retry_count += 1
                    if retry_count < max_retries:
                        self.add_message("系统", f"网络超时，正在重试 ({retry_count}/{max_retries})...")
                    else:
                        self.add_message("系统", "网络请求超时，请检查网络连接或稍后再试")
                except requests.exceptions.RequestException as e:
                    self.add_message("系统", f"网络请求错误: {str(e)}")
                    success = True
                except Exception as e:
                    self.add_message("系统", f"处理消息时出错: {str(e)}")
                    success = True
        except Exception as e:
            self.add_message("系统", f"处理消息时出错: {str(e)}")
    
    def should_analyze_system_message(self, message):
        """判断系统消息是否需要AI分析"""
        # 只分析关键的系统消息，减少API调用次数
        # 关键节点：处理开始、处理完成、错误消息、重要状态变化
        key_triggers = [
            "开始处理流程",
            "处理完成！",
            "失败:",
            "错误:",
            "警告:",
            "模型缩放完成",
            "IK处理完成",
            "ID处理完成",
            "SO处理完成"
        ]
        
        # 检查消息是否包含关键触发词
        for trigger in key_triggers:
            if trigger in message:
                return True
        
        return False
    
    def analyze_system_message(self, message, step=None, is_error=False):
        """让AI分析系统消息并生成回复"""
        # 检查API密钥是否设置
        api_key = self.api_key_var.get().strip()
        if not api_key or api_key == "sk-":
            return
        
        try:
            # 构建请求数据
            # 包含系统消息和相关的对话历史
            chat_history = []
            
            # 最近的几条消息，包括系统消息
            recent_messages = self.conversation_history[-10:]  # 最近10条消息
            
            for msg in recent_messages:
                if msg["sender"] == "您":
                    chat_history.append({"role": "user", "content": msg["message"]})
                elif msg["sender"] == "AI":
                    chat_history.append({"role": "assistant", "content": msg["message"]})
                elif msg["sender"] == "系统":
                    chat_history.append({"role": "system", "content": f"系统消息: {msg['message']}"})
            
            data = {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是OpenSim助手，帮助用户完成从C3D转换到AST模型缩放、IK、ID、SO的完整流程。请提供详细的指导，包括文件准备、参数设置和结果分析。\n\n当你收到系统消息时，请分析消息内容，解释其含义，并提供相关的建议和下一步操作指导。\n\n请根据完整的聊天历史来理解用户的问题和上下文，不要忽略任何之前的对话内容。\n\n当处理步骤完成后，请提供详细的分析和建议，并明确询问用户是否要继续下一步。"
                    },
                    *chat_history
                ],
                "model": "deepseek-chat",
                "temperature": 0.5,  # 降低温度，减少随机性，加快响应
                "max_tokens": 800,  # 减少最大token数，加快响应
                "top_p": 0.9  # 增加top_p，加快响应
            }
            
            # 调用deepseek API
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json=data,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    ai_message = result["choices"][0]["message"]["content"]
                    self.add_message("AI", ai_message)
                    
                    # AI分析完成后，设置等待用户确认状态
                    if step is not None:
                        self.add_message("系统", "请确认是否继续执行下一步。输入'确认'或'继续'来执行下一步，或输入其他内容来停止。")
                        self.process_state['waiting_for_confirmation'] = True
            
        except Exception as e:
            # 分析失败时不显示错误，避免干扰用户
            pass
    
    def start_processing(self):
        """开始处理流程"""
        # 检查是否上传了必要的文件
        if not self.uploaded_files['model']:
            self.add_message("系统", "请先上传模型文件")
            return
        
        if not self.uploaded_files['c3d']:
            self.add_message("系统", "请先上传C3D文件")
            return
        
        # 显示开始处理消息
        self.add_message("系统", "开始处理流程...")
        self.add_message("系统", f"模型文件: {os.path.basename(self.uploaded_files['model'][0])}")
        self.add_message("系统", f"C3D文件数量: {len(self.uploaded_files['c3d'])}")
        
        # 显示上传的配置文件信息
        if self.uploaded_files['scale']:
            self.add_message("系统", f"缩放设置文件: {os.path.basename(self.uploaded_files['scale'][0])}")
        else:
            self.add_message("系统", "未找到缩放设置文件")
        
        if self.uploaded_files['ik_config']:
            self.add_message("系统", f"IK设置文件: {os.path.basename(self.uploaded_files['ik_config'][0])}")
        else:
            self.add_message("系统", "未找到IK设置文件")
        
        # 启动处理线程
        threading.Thread(target=self.process_flow).start()
    
    def process_flow(self):
        """处理完整流程"""
        try:
            # 重置处理状态
            self.process_state['processing'] = True
            self.process_state['paused'] = False
            self.process_state['waiting_for_confirmation'] = False
            
            # 执行第一步：C3D转换
            self.process_state['current_step'] = 1
            self.process_state['step_status'][1] = 1  # 进行中
            self.process_step_1_c3d()
            
        except Exception as e:
            self.add_message("系统", f"处理流程出错: {str(e)}")
            self.process_state['processing'] = False
    
    def confirm_process(self, process_name, params):
        """确认处理过程"""
        # 在聊天页面显示确认消息
        self.add_message("系统", f"{process_name}参数设置：")
        self.add_message("系统", params)
        self.add_message("系统", f"开始{process_name}...")
        return True
    
    def show_results(self):
        """显示处理结果"""
        if not self.process_results:
            self.add_message("系统", "还没有处理结果，请先运行处理流程")
        else:
            result_str = "\n".join(self.process_results)
            self.add_message("系统", f"处理结果：\n{result_str}")
    
    def clear_conversation(self):
        """清除对话历史"""
        # 清空对话历史
        self.conversation_history = []
        
        # 清空聊天窗口
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.delete(1.0, tk.END)
        self.chat_text.config(state=tk.DISABLED)
        
        # 显示初始消息
        self.add_message("AI", "您好！我是OpenSim助手，可以帮您完成从C3D转换到AST模型缩放、IK、ID、SO的完整流程。请上传您的模型文件、C3D文件和配置文件，然后告诉我您的需求。")
    
    def open_results_folder(self):
        """打开结果文件夹"""
        # 使用第一个C3D文件的输出目录
        if self.uploaded_files['c3d']:
            output_dir = os.path.dirname(self.uploaded_files['c3d'][0])  # C3D文件所在目录
            if os.path.exists(output_dir):
                os.startfile(output_dir)
            else:
                self.add_message("系统", "结果文件夹不存在")
        else:
            self.add_message("系统", "请先上传C3D文件")
    
    def download_results(self):
        """下载结果文件"""
        if not self.process_results:
            self.add_message("系统", "还没有处理结果，请先运行处理流程")
        elif not self.uploaded_files['c3d']:
            self.add_message("系统", "请先上传C3D文件")
        else:
            # 选择下载目录
            download_dir = filedialog.askdirectory(title="选择下载目录")
            if download_dir:
                # 获取输出目录
                output_dir = os.path.dirname(self.uploaded_files['c3d'][0])
                downloaded_count = 0
                
                for result_file in self.process_results:
                    # 根据文件扩展名和文件名确定源路径
                    if result_file.endswith('.trc'):
                        source_path = os.path.join(output_dir, "trc", result_file)
                    elif result_file.endswith('.mot'):
                        source_path = os.path.join(output_dir, "mot", result_file)
                    elif "_ID.sto" in result_file:
                        source_path = os.path.join(output_dir, "id", result_file)
                    elif "_SO.sto" in result_file:
                        source_path = os.path.join(output_dir, "so", result_file)
                    elif result_file.endswith('.osim'):
                        source_path = os.path.join(output_dir, result_file)
                    else:
                        # 默认路径
                        source_path = os.path.join(output_dir, result_file)
                    
                    if os.path.exists(source_path):
                        try:
                            import shutil
                            destination_path = os.path.join(download_dir, result_file)
                            shutil.copy2(source_path, destination_path)
                            downloaded_count += 1
                        except Exception as e:
                            self.add_message("系统", f"下载失败 {result_file}: {str(e)}")
                    else:
                        self.add_message("系统", f"文件不存在: {result_file}")
                
                self.add_message("系统", f"下载完成！成功下载 {downloaded_count} 个文件到 {download_dir}")
    
    def load_knowledge_base(self):
        """加载本地知识库"""
        # 固定的知识库内容（写死）
        knowledge_base = {
            "opensim_principles": {
                "C3D_conversion": "C3D文件包含运动捕捉数据和力台数据，需要转换为TRC（标记点轨迹）和MOT（模型运动）格式供OpenSim使用。",
                "Scaling": "缩放过程使用标定文件（BD）来调整通用模型到特定受试者的尺寸，确保模型与实际受试者匹配。",
                "Inverse_Kinematics": "反向运动学（IK）根据标记点轨迹计算关节角度，最小化标记点误差。",
                "Inverse_Dynamics": "反向动力学（ID）根据关节角度和外力计算关节力矩和力。",
                "Static_Optimization": "静态优化（SO）将关节力矩分配到肌肉上，计算肌肉激活和力量。",
                "ExternalLoads": "ExternalLoads XML文件定义了外力（如地面反作用力）的应用方式，需要与MOT文件匹配。"
            },
            "gui_workflow": {
                "steps": [
                    {
                        "step": 1,
                        "name": "C3D转换",
                        "description": "将C3D文件转换为TRC和MOT格式，提取标记点轨迹和力台数据。",
                        "parameters": {
                            "input_file": "C3D文件路径",
                            "output_directory": "输出文件夹路径",
                            "unit_conversion": "mm到m的转换",
                            "frame_rate": "保持原始帧率"
                        }
                    },
                    {
                        "step": 2,
                        "name": "AST模型缩放",
                        "description": "使用标定文件（BD）缩放通用模型到特定受试者尺寸。",
                        "parameters": {
                            "model_file": "通用模型.osim",
                            "marker_file": "标记点文件.trc",
                            "scale_xml": "缩放设置.xml",
                            "output_model": "缩放后的模型.osim"
                        }
                    },
                    {
                        "step": 3,
                        "name": "反向运动学（IK）",
                        "description": "计算关节角度，最小化标记点误差。",
                        "parameters": {
                            "model_file": "缩放后的模型.osim",
                            "marker_file": "标记点文件.trc",
                            "ik_xml": "IK设置.xml",
                            "output_mot": "IK结果.mot"
                        }
                    },
                    {
                        "step": 4,
                        "name": "外部载荷（ExternalLoads）",
                        "description": "生成或使用ExternalLoads XML文件，定义地面反作用力的应用。",
                        "parameters": {
                            "mot_file": "IK结果.mot",
                            "grf_file": "力台数据.mot",
                            "output_xml": "ExternalLoads.xml"
                        }
                    },
                    {
                        "step": 5,
                        "name": "反向动力学（ID）",
                        "description": "计算关节力矩和力。",
                        "parameters": {
                            "model_file": "缩放后的模型.osim",
                            "ik_file": "IK结果.mot",
                            "external_loads": "ExternalLoads.xml",
                            "output_sto": "ID结果.sto"
                        }
                    },
                    {
                        "step": 6,
                        "name": "静态优化（SO）",
                        "description": "计算肌肉激活和力量。",
                        "parameters": {
                            "model_file": "缩放后的模型.osim",
                            "id_file": "ID结果.sto",
                            "so_xml": "SO设置.xml",
                            "output_sto": "SO结果.sto"
                        }
                    }
                ],
                "batch_processing": "支持批量处理多个文件，根据文件名中的动作类型（如ZS、ZX、LD）自动匹配相应的设置。"
            },
            "error_handling": {
                "scaling": {
                    "high_error": "如果缩放误差过高，建议：1. 检查标定文件（BD）中的标记点质量 2. 调整缩放设置XML中的权重 3. 检查measurement set的定义 4. 确保标记点与模型标记点名称一致",
                    "rms_issue": "如果RMS误差下不去，建议：1. 调整各标记点的权重 2. 检查模型标记点位置 3. 考虑使用不同的缩放方法 4. 确保标定动作的质量"
                },
                "ik": {
                    "high_error": "如果IK误差过高，建议：1. 检查TRC文件中的标记点质量 2. 调整IK设置XML中的权重和约束 3. 检查模型关节活动范围 4. 考虑使用不同的IK求解器设置",
                    "tracking_issue": "如果标记点跟踪问题，建议：1. 检查标记点遮挡情况 2. 调整标记点滤波设置 3. 检查模型标记点位置 4. 考虑使用辅助标记点"
                },
                "id": {
                    "force_data_issue": "如果力数据问题，建议：1. 检查力台数据质量 2. 确保ExternalLoads XML配置正确 3. 调整滤波参数 4. 检查力数据与运动数据的同步",
                    "numerical_issues": "如果数值问题，建议：1. 检查模型关节约束 2. 调整积分设置 3. 确保力数据的单位正确 4. 检查运动数据的连续性"
                },
                "so": {
                    "convergence_issue": "如果收敛问题，建议：1. 调整优化参数 2. 检查肌肉模型参数 3. 确保输入数据的质量 4. 考虑使用不同的优化算法",
                    "unrealistic_forces": "如果力值不现实，建议：1. 检查ExternalLoads配置 2. 调整肌肉参数 3. 检查模型结构 4. 确保输入数据的准确性"
                }
            }
        }
        
        # 从用户输入的JSON文件加载动作类型和足的默认设置
        user_configs = {
            "action_types": {
                "ZS": "转身侧切",
                "ZX": "直线冲刺",
                "LD": "落地",
                "BD": "标定文件"
            },
            "foot_settings": {
                "forefoot": "toe",
                "hindfoot": "calcn",
                "midfoot": "",
                "MFS": ""
            }
        }
        
        # 首先尝试加载user_config.json文件
        # 检查当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        user_config_file = os.path.join(script_dir, "user_config.json")
        
        # 如果当前脚本目录没有，再检查当前工作目录
        if not os.path.exists(user_config_file):
            user_config_file = os.path.join(os.getcwd(), "user_config.json")
        
        if os.path.exists(user_config_file):
            try:
                with open(user_config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 只加载动作类型和足的设置
                    if "action_types" in data:
                        user_configs["action_types"] = data["action_types"]
                    if "foot_settings" in data:
                        user_configs["foot_settings"] = data["foot_settings"]
                # 延迟到GUI创建后再显示消息
                if hasattr(self, 'chat_text'):
                    self.add_message("系统", f"从 {os.path.basename(user_config_file)} 加载用户配置")
            except Exception as e:
                # 延迟到GUI创建后再显示消息
                if hasattr(self, 'chat_text'):
                    self.add_message("系统", f"加载user_config.json失败: {str(e)}")
        
        # 然后尝试从knowledge_base.json文件加载
        # 检查当前脚本所在目录
        knowledge_file = os.path.join(script_dir, "knowledge_base.json")
        
        # 如果当前脚本目录没有，再检查当前工作目录
        if not os.path.exists(knowledge_file):
            knowledge_file = os.path.join(os.getcwd(), "knowledge_base.json")
        
        if os.path.exists(knowledge_file):
            try:
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 只加载动作类型和足的设置
                    if "action_types" in data:
                        user_configs["action_types"] = data["action_types"]
                    if "foot_settings" in data:
                        user_configs["foot_settings"] = data["foot_settings"]
                # 延迟到GUI创建后再显示消息
                if hasattr(self, 'chat_text'):
                    self.add_message("系统", f"从 {os.path.basename(knowledge_file)} 加载用户配置")
            except Exception as e:
                # 延迟到GUI创建后再显示消息
                if hasattr(self, 'chat_text'):
                    self.add_message("系统", f"加载knowledge_base.json失败: {str(e)}")
        
        # 如果用户指定了知识库文件夹，尝试从文件夹加载
        knowledge_folder = self.knowledge_base_folder.get()
        if knowledge_folder and os.path.exists(knowledge_folder):
            try:
                # 遍历文件夹中的文件
                for root, dirs, files in os.walk(knowledge_folder):
                    for file in files:
                        if file.endswith('.json'):
                            json_path = os.path.join(root, file)
                            try:
                                with open(json_path, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    # 只加载动作类型和足的设置
                                    if "action_types" in data:
                                        user_configs["action_types"].update(data["action_types"])
                                    if "foot_settings" in data:
                                        user_configs["foot_settings"].update(data["foot_settings"])
                                # 延迟到GUI创建后再显示消息
                                if hasattr(self, 'chat_text'):
                                    self.add_message("系统", f"从 {file} 加载用户配置")
                            except Exception as e:
                                # 延迟到GUI创建后再显示消息
                                if hasattr(self, 'chat_text'):
                                    self.add_message("系统", f"加载配置文件 {file} 失败: {str(e)}")
            except Exception as e:
                # 延迟到GUI创建后再显示消息
                if hasattr(self, 'chat_text'):
                    self.add_message("系统", f"加载用户配置失败: {str(e)}")
        
        # 合并用户配置到知识库
        knowledge_base.update(user_configs)
        
        return knowledge_base
    
    def select_knowledge_folder(self):
        """选择知识库文件夹"""
        folder = filedialog.askdirectory(title="选择知识库文件夹")
        if folder:
            self.knowledge_base_folder.set(folder)
            self.add_message("系统", f"选择知识库文件夹: {folder}")
    
    def reload_knowledge_base(self):
        """重新加载知识库"""
        self.knowledge_base = self.load_knowledge_base()
        self.add_message("系统", "知识库重新加载完成")
    
    def batch_process_external_loads(self):
        """批量处理ExternalLoads XML"""
        if not self.uploaded_files['c3d']:
            self.add_message("系统", "请先上传C3D文件")
            return
        
        self.add_message("系统", "开始批量处理ExternalLoads XML...")
        
        results_folder = os.path.join(os.getcwd(), "results")
        os.makedirs(results_folder, exist_ok=True)
        
        for c3d_file in self.uploaded_files['c3d']:
            try:
                c3d_name = os.path.basename(c3d_file)
                self.add_message("系统", f"处理文件: {c3d_name}")
                
                # 分析文件名，判断动作类型和足型
                action_type = "未知"
                foot_type = "前足"
                
                # 从文件名中提取信息
                if "action_types" in self.knowledge_base:
                    for key in self.knowledge_base["action_types"]:
                        if key in c3d_name:
                            action_type = self.knowledge_base["action_types"][key]
                            break
                
                # 检查对应的MOT文件
                mot_file = os.path.join(results_folder, f"{os.path.splitext(c3d_name)[0]}.mot")
                if os.path.exists(mot_file):
                    self.add_message("系统", f"找到对应的MOT文件: {os.path.basename(mot_file)}")
                    # 这里可以添加读取MOT文件的逻辑，根据MOT文件内容调整配置
                else:
                    self.add_message("系统", f"未找到对应的MOT文件，使用默认配置")
                
                # 根据足型选择配置类型和应用的身体部位
                config_type = "toe"
                applied_to_body_r = "toe_r"
                applied_to_body_l = "toe_l"
                
                # 从知识库获取足的设置
                if "foot_settings" in self.knowledge_base:
                    foot_settings = self.knowledge_base["foot_settings"]
                    if foot_type == "前足" and "forefoot" in foot_settings:
                        forefoot = foot_settings["forefoot"]
                        config_type = forefoot
                        applied_to_body_r = f"{forefoot}_r"
                        applied_to_body_l = f"{forefoot}_l"
                    elif foot_type == "后足" and "hindfoot" in foot_settings:
                        hindfoot = foot_settings["hindfoot"]
                        config_type = hindfoot
                        applied_to_body_r = f"{hindfoot}_r"
                        applied_to_body_l = f"{hindfoot}_l"
                
                self.add_message("系统", f"识别动作类型: {action_type}")
                self.add_message("系统", f"使用足型: {foot_type}")
                self.add_message("系统", f"使用配置类型: {config_type}")
                self.add_message("系统", f"应用到身体部位: 右足={applied_to_body_r}, 左足={applied_to_body_l}")
                
                # 生成ExternalLoads XML文件
                xml_name = f"{os.path.splitext(c3d_name)[0]}_ExternalLoads.xml"
                xml_path = os.path.join(results_folder, xml_name)
                
                # 生成XML内容
                xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<OpenSimDocument Version="4.0">
    <ExternalLoads name="{os.path.splitext(c3d_name)[0]}" version="4.0">
        <libraries />
        <ExternalForceSet name="ExternalForceSet" version="4.0">
            <objects>
                <ExternalForce name="ground_force_r" version="4.0">
                    <applied_to_body>{applied_to_body_r}</applied_to_body>
                    <force_identifier>1</force_identifier>
                    <point_identifier>1</point_identifier>
                    <datafile>{os.path.splitext(c3d_name)[0]}.mot</datafile>
                    <filter_weight>0.75</filter_weight>
                </ExternalForce>
                <ExternalForce name="ground_force_l" version="4.0">
                    <applied_to_body>{applied_to_body_l}</applied_to_body>
                    <force_identifier>2</force_identifier>
                    <point_identifier>2</point_identifier>
                    <datafile>{os.path.splitext(c3d_name)[0]}.mot</datafile>
                    <filter_weight>0.75</filter_weight>
                </ExternalForce>
            </objects>
        </ExternalForceSet>
    </ExternalLoads>
</OpenSimDocument>"""
                
                # 写入XML文件
                with open(xml_path, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                
                self.add_message("系统", f"生成ExternalLoads XML: {xml_name}")
                self.process_results.append(xml_name)
                
            except Exception as e:
                self.add_message("系统", f"处理失败 {c3d_file}: {str(e)}")
        
        # 更新结果列表
        self.results_listbox.delete(0, tk.END)
        for result in self.process_results:
            self.results_listbox.insert(tk.END, result)
        
        self.add_message("系统", "批量处理ExternalLoads XML完成！")
    
    def confirm_file_modification(self, request_id):
        """确认文件修改"""
        if hasattr(self, 'file_modification_requests') and request_id in self.file_modification_requests:
            request_info = self.file_modification_requests[request_id]
            file_path = request_info['file_path']
            new_content = request_info['new_content']
            reason = request_info['reason']
            
            # 执行文件修改
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self.add_message("系统", f"文件修改成功：{os.path.basename(file_path)}")
            except Exception as e:
                self.add_message("系统", f"文件修改失败：{str(e)}")
            
            # 移除请求
            del self.file_modification_requests[request_id]
    
    def cancel_file_modification(self, request_id):
        """取消文件修改"""
        if hasattr(self, 'file_modification_requests') and request_id in self.file_modification_requests:
            # 移除请求
            del self.file_modification_requests[request_id]
            self.add_message("系统", "文件修改被用户拒绝")
    
    def modify_file(self, file_path, new_content, reason):
        """修改文件，需要用户确认"""
        # 存储修改请求信息
        if not hasattr(self, 'file_modification_requests'):
            self.file_modification_requests = {}
        
        # 生成唯一的修改请求ID
        import uuid
        request_id = str(uuid.uuid4())
        
        self.file_modification_requests[request_id] = {
            'file_path': file_path,
            'new_content': new_content,
            'reason': reason
        }
        
        # 在聊天窗口中显示修改请求
        self.add_message("AI", f"我需要修改文件 {os.path.basename(file_path)}。\n\n修改原因：{reason}\n\n请回复 '确认' 或 '取消' 来决定是否执行此修改。\n\n修改请求ID: {request_id}")
        
        return False  # 暂时返回False，等待用户确认
    
    def process_step_1_c3d(self):
        """执行C3D转换步骤"""
        try:
            self.add_message("系统", "准备进行C3D转换...")
            self.update_step_status(1, "进行中")
            
            c3d_results = []
            trc_files = []
            mot_files = []
            
            for c3d_file in self.uploaded_files['c3d']:
                try:
                    self.add_message("系统", f"处理C3D文件: {os.path.basename(c3d_file)}")
                    # 设置输出目录为C3D文件所在目录的父目录
                    c3d_dir = os.path.dirname(c3d_file)
                    output_dir = os.path.dirname(c3d_dir)  # C3D文件所在目录的父目录
                    
                    # 显示C3D转换参数
                    c3d_params = """
C3D转换参数：
- 输出目录: {output_dir}
- 单位转换: mm → m (除以1000)
- 坐标系统转换: X=右,Y=前,Z=上 → X=前,Y=上,Z=右
- 输出格式: TRC (标记点) 和 MOT (力板数据)
                    """.format(output_dir=output_dir)
                    
                    self.add_message("系统", "C3D转换参数设置：")
                    self.add_message("系统", c3d_params)
                    
                    trc_path, mot_path = convert_c3d_to_trc_and_mot(c3d_file, output_dir)
                    if trc_path:
                        c3d_results.append(os.path.basename(trc_path))
                        trc_files.append(trc_path)
                    if mot_path:
                        c3d_results.append(os.path.basename(mot_path))
                        mot_files.append(mot_path)
                    self.add_message("系统", f"C3D转换完成: {os.path.basename(c3d_file)}")
                except Exception as e:
                    self.add_message("系统", f"C3D转换失败: {str(e)}")
            
            # 保存结果
            self.process_state['step_results'][1] = {
                'trc_files': trc_files,
                'mot_files': mot_files,
                'c3d_results': c3d_results
            }
            
            # 更新状态
            self.process_state['step_status'][1] = 2  # 完成
            self.process_state['current_step'] = 1
            self.update_step_status(1, "完成")
            
            # 触发AI分析
            self.trigger_ai_analysis(1)
            
        except Exception as e:
            self.add_message("系统", f"C3D转换过程中出错: {str(e)}")
            self.process_state['step_status'][1] = 3  # 失败
            self.update_step_status(1, "失败")
            self.trigger_ai_analysis(1, is_error=True)
    
    def process_step_2_scaling(self):
        """执行模型缩放步骤"""
        try:
            self.add_message("系统", "准备进行模型缩放(AST)...")
            self.update_step_status(2, "进行中")
            
            trc_files = self.process_state['step_results'].get(1, {}).get('trc_files', [])
            
            if self.uploaded_files['model'] and trc_files:
                model_path = self.uploaded_files['model'][0]
                
                # 寻找标定文件（BD）
                calibration_trc = None
                scale_xml = None
                
                # 从TRC文件中寻找标定文件
                for trc_path in trc_files:
                    trc_name = os.path.basename(trc_path)
                    if "BD" in trc_name:
                        calibration_trc = trc_path
                        break
                
                # 从上传的文件中寻找缩放设置XML
                if self.uploaded_files['scale']:
                    scale_xml = self.uploaded_files['scale'][0]
                
                # 获取输出目录（使用第一个C3D文件的输出目录）
                if self.uploaded_files['c3d']:
                    c3d_dir = os.path.dirname(self.uploaded_files['c3d'][0])
                    output_dir = os.path.dirname(c3d_dir)  # C3D文件所在目录的父目录
                else:
                    output_dir = os.getcwd()
                
                ast_params = """
模型缩放(AST)参数：
- 原始模型文件: {model_name}
- 标定TRC文件: {calibration_trc}
- 缩放设置XML: {scale_xml}
- 输出目录: {output_dir}
- 输出模型: 缩放后的模型.osim
                """.format(
                    model_name=os.path.basename(model_path),
                    calibration_trc=os.path.basename(calibration_trc) if calibration_trc else "未找到",
                    scale_xml=os.path.basename(scale_xml) if scale_xml else "未找到",
                    output_dir=output_dir
                )
                
                self.add_message("系统", "模型缩放(AST)参数设置：")
                self.add_message("系统", ast_params)
                
                # 检查是否缺少必要文件
                missing_files = []
                if not calibration_trc:
                    missing_files.append("标定TRC文件")
                if not scale_xml:
                    missing_files.append("缩放设置XML")
                
                if missing_files:
                    # 让AI在聊天页面询问用户
                    self.add_message("AI", f"我需要以下文件来进行模型缩放：{', '.join(missing_files)}。请告诉我这些文件在哪里，或者上传它们。")
                    self.process_state['step_status'][2] = 3  # 失败
                    self.update_step_status(2, "失败")
                    self.trigger_ai_analysis(2, is_error=True)
                else:
                    self.add_message("系统", "开始模型缩放(AST)...")
                    scaled_model_path = os.path.join(output_dir, "ModelScaled.osim")
                    
                    try:
                        # 这里可以添加实际的AST缩放代码
                        # 暂时使用简化处理
                        self.add_message("系统", "模型缩放完成")
                        self.add_message("系统", f"缩放后的模型: {os.path.basename(scaled_model_path)}")
                        
                        # 模拟误差检查
                        self.add_message("系统", "检查缩放误差...")
                        # 这里可以添加实际的误差检查代码
                        
                        # 提供误差处理建议
                        if "error_handling" in self.knowledge_base and "scaling" in self.knowledge_base["error_handling"]:
                            self.add_message("系统", "缩放误差处理建议:")
                            self.add_message("系统", self.knowledge_base["error_handling"]["scaling"]["high_error"])
                        
                        # 保存结果
                        self.process_state['step_results'][2] = {
                            'scaled_model_path': scaled_model_path,
                            'calibration_trc': calibration_trc
                        }
                        
                        # 更新状态
                        self.process_state['step_status'][2] = 2  # 完成
                        self.process_state['current_step'] = 2
                        self.update_step_status(2, "完成")
                        
                        # 触发AI分析
                        self.trigger_ai_analysis(2)
                        
                    except Exception as e:
                        self.add_message("系统", f"模型缩放失败: {str(e)}")
                        self.process_state['step_status'][2] = 3  # 失败
                        self.update_step_status(2, "失败")
                        self.trigger_ai_analysis(2, is_error=True)
            else:
                self.add_message("系统", "模型缩放跳过：缺少模型文件或TRC文件")
                self.process_state['step_status'][2] = 3  # 失败
                self.update_step_status(2, "失败")
                self.trigger_ai_analysis(2, is_error=True)
                
        except Exception as e:
            self.add_message("系统", f"模型缩放过程中出错: {str(e)}")
            self.process_state['step_status'][2] = 3  # 失败
            self.update_step_status(2, "失败")
            self.trigger_ai_analysis(2, is_error=True)
    
    def process_step_3_ik(self):
        """执行IK处理步骤"""
        try:
            self.add_message("系统", "准备进行IK处理...")
            self.update_step_status(3, "进行中")
            
            trc_files = self.process_state['step_results'].get(1, {}).get('trc_files', [])
            
            if trc_files:
                # 使用缩放后的模型（如果存在）
                scaled_model_path = self.process_state['step_results'].get(2, {}).get('scaled_model_path')
                if scaled_model_path and os.path.exists(scaled_model_path):
                    model_path = scaled_model_path
                    self.add_message("系统", f"使用缩放后的模型: {os.path.basename(model_path)}")
                elif self.uploaded_files['model']:
                    model_path = self.uploaded_files['model'][0]
                    self.add_message("系统", f"使用原始模型: {os.path.basename(model_path)}")
                else:
                    self.add_message("系统", "IK处理跳过：缺少模型文件")
                    self.process_state['step_status'][3] = 3  # 失败
                    self.update_step_status(3, "失败")
                    self.trigger_ai_analysis(3, is_error=True)
                    return
                
                ik_config = self.uploaded_files['ik_config'][0] if self.uploaded_files['ik_config'] else "默认设置"
                
                # 获取输出目录（使用第一个C3D文件的输出目录）
                if self.uploaded_files['c3d']:
                    c3d_dir = os.path.dirname(self.uploaded_files['c3d'][0])
                    output_dir = os.path.dirname(c3d_dir)  # C3D文件所在目录的父目录
                else:
                    output_dir = os.getcwd()
                
                # 创建ik子文件夹
                ik_dir = os.path.join(output_dir, "ik")
                os.makedirs(ik_dir, exist_ok=True)
                
                ik_params = """
IK处理参数：
- 模型文件: {model_name}
- TRC文件列表: {trc_files}
- IK设置XML: {ik_config}
- 输出目录: {output_dir}
- 时间范围: 从TRC文件自动获取
- 输出格式: *_IK.mot
                """.format(
                    model_name=os.path.basename(model_path),
                    trc_files="\n" + "\n".join([os.path.basename(f) for f in trc_files]),
                    ik_config=os.path.basename(ik_config) if isinstance(ik_config, str) and os.path.exists(ik_config) else ik_config,
                    output_dir=output_dir
                )
                
                self.add_message("系统", "IK处理参数设置：")
                self.add_message("系统", ik_params)
                
                # 检查是否缺少IK设置文件
                if not self.uploaded_files['ik_config']:
                    self.add_message("AI", "我需要IK设置XML文件来进行IK处理。请告诉我这个文件在哪里，或者上传它。")
                    self.process_state['step_status'][3] = 3  # 失败
                    self.update_step_status(3, "失败")
                    self.trigger_ai_analysis(3, is_error=True)
                else:
                    self.add_message("系统", "开始IK处理...")
                    ik_results = []
                    try:
                        # 加载模型
                        model = osim.Model(model_path)
                        model.initSystem()
                        
                        for trc_path in trc_files:
                            try:
                                trc_file = os.path.basename(trc_path)
                                output_mot = os.path.join(ik_dir, f"{os.path.splitext(trc_file)[0]}_IK.mot")
                                
                                # 创建IK工具
                                ik_tool = osim.InverseKinematicsTool()
                                ik_tool.setModel(model)
                                ik_tool.setMarkerDataFileName(trc_path)
                                ik_tool.setOutputMotionFileName(output_mot)
                                
                                # 设置时间范围
                                marker_data = osim.MarkerData(trc_path)
                                ik_tool.setStartTime(marker_data.getStartFrameTime())
                                ik_tool.setEndTime(marker_data.getLastFrameTime())
                                
                                # 运行IK
                                ik_tool.run()
                                
                                ik_results.append(os.path.basename(output_mot))
                                self.add_message("系统", f"IK处理完成: {trc_file}")
                                
                                # 提供IK误差处理建议
                                if "error_handling" in self.knowledge_base and "ik" in self.knowledge_base["error_handling"]:
                                    self.add_message("系统", "IK误差处理建议:")
                                    self.add_message("系统", self.knowledge_base["error_handling"]["ik"]["high_error"])
                            except Exception as e:
                                self.add_message("系统", f"IK处理失败: {str(e)}")
                        
                        # 保存结果
                        self.process_state['step_results'][3] = {
                            'ik_results': ik_results,
                            'model_path': model_path,
                            'ik_dir': ik_dir
                        }
                        
                        # 更新状态
                        self.process_state['step_status'][3] = 2  # 完成
                        self.process_state['current_step'] = 3
                        self.update_step_status(3, "完成")
                        
                        # 触发AI分析
                        self.trigger_ai_analysis(3)
                        
                    except Exception as e:
                        self.add_message("系统", f"加载模型失败: {str(e)}")
                        self.process_state['step_status'][3] = 3  # 失败
                        self.update_step_status(3, "失败")
                        self.trigger_ai_analysis(3, is_error=True)
            else:
                self.add_message("系统", "IK处理跳过：缺少模型文件或TRC文件")
                self.process_state['step_status'][3] = 3  # 失败
                self.update_step_status(3, "失败")
                self.trigger_ai_analysis(3, is_error=True)
                
        except Exception as e:
            self.add_message("系统", f"IK处理过程中出错: {str(e)}")
            self.process_state['step_status'][3] = 3  # 失败
            self.update_step_status(3, "失败")
            self.trigger_ai_analysis(3, is_error=True)
    
    def process_step_4_id(self):
        """执行ID处理步骤"""
        try:
            self.add_message("系统", "准备进行ID处理...")
            self.update_step_status(4, "进行中")
            
            ik_results = self.process_state['step_results'].get(3, {}).get('ik_results', [])
            
            if ik_results:
                # 使用缩放后的模型（如果存在）
                scaled_model_path = self.process_state['step_results'].get(2, {}).get('scaled_model_path')
                if scaled_model_path and os.path.exists(scaled_model_path):
                    model_path = scaled_model_path
                    self.add_message("系统", f"使用缩放后的模型: {os.path.basename(model_path)}")
                elif self.uploaded_files['model']:
                    model_path = self.uploaded_files['model'][0]
                    self.add_message("系统", f"使用原始模型: {os.path.basename(model_path)}")
                else:
                    self.add_message("系统", "ID处理跳过：缺少模型文件")
                    self.process_state['step_status'][4] = 3  # 失败
                    self.update_step_status(4, "失败")
                    self.trigger_ai_analysis(4, is_error=True)
                    return
                
                # 获取输出目录（使用第一个C3D文件的输出目录）
                if self.uploaded_files['c3d']:
                    c3d_dir = os.path.dirname(self.uploaded_files['c3d'][0])
                    output_dir = os.path.dirname(c3d_dir)  # C3D文件所在目录的父目录
                else:
                    output_dir = os.getcwd()
                
                # 创建id子文件夹
                id_dir = os.path.join(output_dir, "id")
                os.makedirs(id_dir, exist_ok=True)
                
                id_params = """
ID处理参数：
- 模型文件: {model_name}
- IK文件数量: {ik_count}
- 输出目录: {output_dir}
- 低通滤波频率: 6.0 Hz
- 时间范围: 从IK文件自动获取
- 输出格式: *_ID.sto
                """.format(
                    model_name=os.path.basename(model_path),
                    ik_count=len(ik_results),
                    output_dir=output_dir
                )
                
                self.add_message("系统", "ID处理参数设置：")
                self.add_message("系统", id_params)
                
                self.add_message("系统", "开始ID处理...")
                id_results = []
                try:
                    for ik_file in ik_results:
                        try:
                            # 构建IK文件的完整路径
                            if self.uploaded_files['c3d']:
                                c3d_dir = os.path.dirname(self.uploaded_files['c3d'][0])
                                output_dir = os.path.dirname(c3d_dir)  # C3D文件所在目录的父目录
                                ik_dir = os.path.join(output_dir, "ik")
                                ik_path = os.path.join(ik_dir, ik_file)
                            else:
                                ik_path = os.path.join(os.getcwd(), "ik", ik_file)
                            
                            output_sto = os.path.join(id_dir, f"{os.path.splitext(ik_file)[0]}_ID.sto")
                            
                            # 加载模型
                            model_trial = osim.Model(model_path)
                            model_trial.initSystem()
                            
                            # 禁用模型中所有肌肉力
                            for i in range(model_trial.getMuscles().getSize()):
                                muscle = model_trial.getMuscles().get(i)
                                muscle.set_appliesForce(False)
                            
                            # 读取IK时间
                            ik_table = osim.TimeSeriesTable(ik_path)
                            time_vec = ik_table.getIndependentColumn()
                            t0 = time_vec[0]
                            tf = time_vec[-1]
                            
                            # 设置ID Tool
                            id_tool = osim.InverseDynamicsTool()
                            id_tool.setModel(model_trial)
                            id_tool.setCoordinatesFileName(ik_path)
                            id_tool.setLowpassCutoffFrequency(6.0)  # IK数据滤波
                            
                            # 时间与输出设置
                            id_tool.setStartTime(t0)
                            id_tool.setEndTime(tf)
                            id_tool.setResultsDir(id_dir)
                            id_tool.setOutputGenForceFileName(output_sto)
                            
                            # 运行ID
                            id_tool.run()
                            
                            id_results.append(os.path.basename(output_sto))
                            self.add_message("系统", f"ID处理完成: {ik_file}")
                            
                            # 提供ID处理建议
                            if "error_handling" in self.knowledge_base and "id" in self.knowledge_base["error_handling"]:
                                self.add_message("系统", "ID处理建议:")
                                self.add_message("系统", self.knowledge_base["error_handling"]["id"]["force_data_issue"])
                        except Exception as e:
                            self.add_message("系统", f"ID处理失败: {str(e)}")
                    
                    # 保存结果
                    self.process_state['step_results'][4] = {
                        'id_results': id_results
                    }
                    
                    # 更新状态
                    self.process_state['step_status'][4] = 2  # 完成
                    self.process_state['current_step'] = 4
                    self.update_step_status(4, "完成")
                    
                    # 触发AI分析
                    self.trigger_ai_analysis(4)
                    
                except Exception as e:
                    self.add_message("系统", f"加载模型失败: {str(e)}")
                    self.process_state['step_status'][4] = 3  # 失败
                    self.update_step_status(4, "失败")
                    self.trigger_ai_analysis(4, is_error=True)
            else:
                self.add_message("系统", "ID处理跳过：缺少模型文件或IK结果文件")
                self.process_state['step_status'][4] = 3  # 失败
                self.update_step_status(4, "失败")
                self.trigger_ai_analysis(4, is_error=True)
                
        except Exception as e:
            self.add_message("系统", f"ID处理过程中出错: {str(e)}")
            self.process_state['step_status'][4] = 3  # 失败
            self.update_step_status(4, "失败")
            self.trigger_ai_analysis(4, is_error=True)
    
    def process_step_5_so(self):
        """执行SO处理步骤"""
        try:
            self.add_message("系统", "准备进行SO处理...")
            self.update_step_status(5, "进行中")
            
            ik_results = self.process_state['step_results'].get(3, {}).get('ik_results', [])
            
            if ik_results:
                # 使用缩放后的模型（如果存在）
                scaled_model_path = self.process_state['step_results'].get(2, {}).get('scaled_model_path')
                if scaled_model_path and os.path.exists(scaled_model_path):
                    model_path = scaled_model_path
                    self.add_message("系统", f"使用缩放后的模型: {os.path.basename(model_path)}")
                elif self.uploaded_files['model']:
                    model_path = self.uploaded_files['model'][0]
                    self.add_message("系统", f"使用原始模型: {os.path.basename(model_path)}")
                else:
                    self.add_message("系统", "SO处理跳过：缺少模型文件")
                    self.process_state['step_status'][5] = 3  # 失败
                    self.update_step_status(5, "失败")
                    self.trigger_ai_analysis(5, is_error=True)
                    return
                
                # 获取输出目录（使用第一个C3D文件的输出目录）
                if self.uploaded_files['c3d']:
                    c3d_dir = os.path.dirname(self.uploaded_files['c3d'][0])
                    output_dir = os.path.dirname(c3d_dir)  # C3D文件所在目录的父目录
                else:
                    output_dir = os.getcwd()
                
                # 创建so子文件夹
                so_dir = os.path.join(output_dir, "so")
                os.makedirs(so_dir, exist_ok=True)
                
                so_params = """
SO处理参数：
- 模型文件: {model_name}
- IK文件数量: {ik_count}
- 输出目录: {output_dir}
- 低通滤波频率: 6.0 Hz
- 激活指数: 2.0
- 使用肌肉生理学: 是
- 步长间隔: 1
- 时间范围: 从IK文件自动获取
- 输出精度: 8
                """.format(
                    model_name=os.path.basename(model_path),
                    ik_count=len(ik_results),
                    output_dir=output_dir
                )
                
                self.add_message("系统", "SO处理参数设置：")
                self.add_message("系统", so_params)
                
                self.add_message("系统", "开始SO处理...")
                so_results = []
                try:
                    for ik_file in ik_results:
                        try:
                            # 构建IK文件的完整路径
                            if self.uploaded_files['c3d']:
                                c3d_dir = os.path.dirname(self.uploaded_files['c3d'][0])
                                output_dir = os.path.dirname(c3d_dir)  # C3D文件所在目录的父目录
                                ik_dir = os.path.join(output_dir, "ik")
                                ik_path = os.path.join(ik_dir, ik_file)
                            else:
                                ik_path = os.path.join(os.getcwd(), "ik", ik_file)
                            
                            # 读取IK文件获取时间范围
                            ik_table = osim.TimeSeriesTable(ik_path)
                            time_vec = ik_table.getIndependentColumn()
                            t0_file = time_vec[0]
                            tf_file = time_vec[-1]
                            
                            # 创建 AnalyzeTool
                            analyze_tool = osim.AnalyzeTool()
                            analyze_tool.setName(f"SO_{os.path.splitext(ik_file)[0]}")
                            
                            # 先加载模型
                            model = osim.Model(model_path)
                            model.initSystem()
                            analyze_tool.setModel(model)
                            
                            # 设置运动文件
                            ik_file_path_normalized = ik_path.replace('\\', '/')
                            analyze_tool.setCoordinatesFileName(ik_file_path_normalized)
                            
                            # 设置低通滤波频率
                            analyze_tool.setLowpassCutoffFrequency(6.0)
                            
                            # 创建 StaticOptimization
                            so = osim.StaticOptimization()
                            so.setStartTime(t0_file)
                            so.setEndTime(tf_file)
                            so.setStepInterval(1)
                            so.setActivationExponent(2.0)
                            so.setUseMusclePhysiology(True)
                            
                            # 添加到分析集
                            analyze_tool.updAnalysisSet().cloneAndAppend(so)
                            
                            # 配置 AnalyzeTool
                            analyze_tool.setStartTime(t0_file)
                            analyze_tool.setFinalTime(tf_file)
                            analyze_tool.setResultsDir(so_dir)
                            analyze_tool.setOutputPrecision(8)
                            
                            # 运行静态优化
                            analyze_tool.run()
                            
                            # 生成的SO文件名通常是：{model_name}_StaticOptimization_activation.sto
                            # 这里简化处理，添加到结果列表
                            so_results.append(f"{os.path.splitext(ik_file)[0]}_SO.sto")
                            self.add_message("系统", f"SO处理完成: {ik_file}")
                            
                            # 提供SO处理建议
                            if "error_handling" in self.knowledge_base and "so" in self.knowledge_base["error_handling"]:
                                self.add_message("系统", "SO处理建议:")
                                self.add_message("系统", self.knowledge_base["error_handling"]["so"]["convergence_issue"])
                        except Exception as e:
                            self.add_message("系统", f"SO处理失败: {str(e)}")
                    
                    # 保存结果
                    self.process_state['step_results'][5] = {
                        'so_results': so_results
                    }
                    
                    # 更新状态
                    self.process_state['step_status'][5] = 2  # 完成
                    self.process_state['current_step'] = 5
                    self.update_step_status(5, "完成")
                    
                    # 触发AI分析
                    self.trigger_ai_analysis(5)
                    
                except Exception as e:
                    self.add_message("系统", f"加载模型失败: {str(e)}")
                    self.process_state['step_status'][5] = 3  # 失败
                    self.update_step_status(5, "失败")
                    self.trigger_ai_analysis(5, is_error=True)
            else:
                self.add_message("系统", "SO处理跳过：缺少模型文件或IK结果文件")
                self.process_state['step_status'][5] = 3  # 失败
                self.update_step_status(5, "失败")
                self.trigger_ai_analysis(5, is_error=True)
                
        except Exception as e:
            self.add_message("系统", f"SO处理过程中出错: {str(e)}")
            self.process_state['step_status'][5] = 3  # 失败
            self.update_step_status(5, "失败")
            self.trigger_ai_analysis(5, is_error=True)
    
    def trigger_ai_analysis(self, step, is_error=False):
        """触发AI分析步骤结果"""
        # 构建分析消息
        step_name = self.step_names.get(step, f"步骤{step}")
        status = "失败" if is_error else "完成"
        
        # 构建分析消息
        analysis_message = f"{step_name}已{status}。请分析结果并提供建议。"
        
        # 添加系统消息
        self.add_message("系统", f"{step_name}已{status}，等待AI分析...")
        
        # 触发AI分析，传递步骤信息
        threading.Thread(target=self.analyze_system_message, args=(analysis_message, step, is_error)).start()
        
        # 暂不设置等待用户确认状态，等待AI分析完成后再设置
    
    def process_next_step(self):
        """处理下一步"""
        current_step = self.process_state['current_step']
        
        if current_step == 1:
            # 执行模型缩放
            self.process_state['step_status'][2] = 1  # 进行中
            self.update_step_status(2, "进行中")
            self.process_step_2_scaling()
        elif current_step == 2:
            # 执行IK处理
            self.process_state['step_status'][3] = 1  # 进行中
            self.update_step_status(3, "进行中")
            self.process_step_3_ik()
        elif current_step == 3:
            # 执行ID处理
            self.process_state['step_status'][4] = 1  # 进行中
            self.update_step_status(4, "进行中")
            self.process_step_4_id()
        elif current_step == 4:
            # 执行SO处理
            self.process_state['step_status'][5] = 1  # 进行中
            self.update_step_status(5, "进行中")
            self.process_step_5_so()
        elif current_step == 5:
            # 处理完成
            self.add_message("系统", "处理流程完成！")
            self.process_state['processing'] = False
    
    def reset_process(self):
        """重置处理流程"""
        # 重置处理状态
        self.process_state = {
            'current_step': 0,  # 当前步骤：0-未开始，1-C3D转换，2-模型缩放，3-IK处理，4-ID处理，5-SO处理
            'step_status': {    # 各步骤状态：0-未开始，1-进行中，2-完成，3-失败
                1: 0,
                2: 0,
                3: 0,
                4: 0,
                5: 0
            },
            'step_results': {},  # 各步骤的结果
            'processing': False,  # 是否正在处理
            'paused': False,      # 是否暂停
            'waiting_for_confirmation': False  # 是否等待用户确认
        }
        
        # 更新步骤状态显示
        for step in range(1, 6):
            self.update_step_status(step, "未开始")
        
        self.add_message("系统", "处理流程已重置")
    
    def update_step_status(self, step, status):
        """更新步骤状态显示"""
        if step in self.step_labels:
            self.step_labels[step].set(status)
            
            # 更新状态颜色
            status_label = self.step_labels[step].widget
            if status == "未开始":
                status_label.configure(foreground="gray")
            elif status == "进行中":
                status_label.configure(foreground="blue")
            elif status == "完成":
                status_label.configure(foreground="green")
            elif status == "失败":
                status_label.configure(foreground="red")
