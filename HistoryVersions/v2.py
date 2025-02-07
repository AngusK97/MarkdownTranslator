import os
import time
import re
import threading
from tkinter import Tk, Button, Label, filedialog, messagebox, StringVar
from tkinter.ttk import Progressbar
from google.cloud import translate_v2 as translate

# 配置 Google Translate API 客户端
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"E:\Download\united-column-450109-f0-98230610e0a0.json"
translate_client = translate.Client()

class TranslationApp:
    def __init__(self, master):
        self.master = master
        master.title("Markdown 翻译工具")
        master.geometry("400x200")

        # 初始化变量
        self.folder_path = StringVar()
        self.folder_path.set("未选择文件夹")

        # UI 元素
        self.label = Label(master, textvariable=self.folder_path)
        self.label.pack(pady=10)

        self.select_button = Button(master, text="选择文件夹", command=self.select_folder)
        self.select_button.pack(pady=5)

        self.translate_button = Button(master, text="开始翻译", command=self.start_translation, state="disabled")
        self.translate_button.pack(pady=5)

        self.close_button = Button(master, text="关闭程序", command=master.quit)
        self.close_button.pack(pady=5)

        # 进度条
        self.progress = Progressbar(master, orient="horizontal", length=200, mode="determinate")
        self.progress.pack(pady=10)

    def select_folder(self):
        """选择文件夹"""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(f"已选择文件夹: {folder_selected}")
            self.translate_button.config(state="normal")  # 启用开始翻译按钮

    def start_translation(self):
        """开始翻译（通过线程执行，避免 UI 卡死）"""
        folder = self.folder_path.get().replace("已选择文件夹: ", "")
        if not folder:
            messagebox.showwarning("警告", "请先选择文件夹！")
            return

        # 禁用按钮防止重复点击
        self.translate_button.config(state="disabled")
        self.select_button.config(state="disabled")

        # 启动线程执行翻译任务
        thread = threading.Thread(target=self.run_translation, args=(folder,))
        thread.start()

    def run_translation(self, folder_path):
        """实际执行翻译任务的函数"""
        try:
            self.progress["value"] = 0
            files = [f for f in os.listdir(folder_path) if f.endswith('.md')]
            total_files = len(files)

            for idx, filename in enumerate(files):
                self.progress["value"] = (idx + 1) / total_files * 100
                self.master.update_idletasks()  # 更新进度条

                file_path = os.path.join(folder_path, filename)
                self.translate_file(file_path)
                time.sleep(0.5)  # 避免 API 速率限制

            messagebox.showinfo("完成", "翻译任务已完成！")
        except Exception as e:
            messagebox.showerror("错误", f"翻译过程中发生错误:\n{str(e)}")
        finally:
            # 重新启用按钮
            self.translate_button.config(state="normal")
            self.select_button.config(state="normal")
            self.progress["value"] = 0

    def translate_file(self, file_path):
        """翻译单个文件"""
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        translated_lines = []
        for line in lines:
            line_content = line.rstrip('\n')
            if not line_content.strip():
                translated_lines.append('\n')
                continue
            translated_line = self.process_markdown_line(line_content)
            translated_lines.append(translated_line + '\n')

        # 保存到 translated 子文件夹
        translated_folder = os.path.join(os.path.dirname(file_path), 'translated')
        os.makedirs(translated_folder, exist_ok=True)
        translated_file_path = os.path.join(translated_folder, os.path.basename(file_path))

        with open(translated_file_path, 'w', encoding='utf-8') as f:
            f.writelines(translated_lines)

    def process_markdown_line(self, line):
        """处理单行 Markdown 格式"""
        patterns = [
            (r'^(\s*[-*+]\s+)(.*)', 'list'),
            (r'^(\s*\d+\.\s+)(.*)', 'ordered_list'),
            (r'^(#+\s+)(.*)', 'header'),
            (r'^(\s*`{3,}\s*.*)', 'code_block'),
            (r'(\[.*?\]\(.*?\))', 'link'),
            (r'(`.+?`)', 'inline_code')
        ]

        for pattern, pattern_type in patterns:
            match = re.match(pattern, line)
            if match:
                if pattern_type in ['list', 'ordered_list', 'header']:
                    symbol, content = match.groups()
                    translated_content = translate_client.translate(content, target_language='en')['translatedText']
                    return f"{symbol}{translated_content}"
                elif pattern_type in ['code_block', 'inline_code', 'link']:
                    return line
        # 普通文本翻译
        return translate_client.translate(line, target_language='en')['translatedText']

if __name__ == '__main__':
    root = Tk()
    app = TranslationApp(root)
    root.mainloop()