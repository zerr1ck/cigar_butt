import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import pandas as pd
import requests
import time
import warnings
import threading
from datetime import datetime

warnings.filterwarnings('ignore')

class StockAnalysisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("股票捡烟蒂策略分析工具 v1.1")
        self.root.geometry("1200x800")
        
        # 设置样式
        self.setup_styles()
        
        # 创建主框架
        self.create_widgets()
        
        # 初始化数据
        self.analysis_result = None
        self.all_data = None
        
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        
    def create_widgets(self):
        """创建界面组件"""
        # 主标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(title_frame, text="股票捡烟蒂策略分析工具", style='Title.TLabel').pack()
        
        # 控制面板
        control_frame = ttk.LabelFrame(self.root, text="参数设置", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        # 参数输入
        param_frame = ttk.Frame(control_frame)
        param_frame.pack(fill='x')
        
        ttk.Label(param_frame, text="最大PB值:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.pb_max_var = tk.StringVar(value="1.2")
        ttk.Entry(param_frame, textvariable=self.pb_max_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(param_frame, text="最大PE值:").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.pe_max_var = tk.StringVar(value="20")
        ttk.Entry(param_frame, textvariable=self.pe_max_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(param_frame, text="最小市值(亿):").grid(row=0, column=4, padx=5, pady=5, sticky='w')
        self.mcap_min_var = tk.StringVar(value="100")
        ttk.Entry(param_frame, textvariable=self.mcap_min_var, width=10).grid(row=0, column=5, padx=5, pady=5)
        
        # 按钮区域
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        self.analyze_btn = ttk.Button(button_frame, text="🔍 开始分析", command=self.start_analysis)
        self.analyze_btn.pack(side='left', padx=5)
        
        self.export_btn = ttk.Button(button_frame, text="💾 导出结果", command=self.export_results, state='disabled')
        self.export_btn.pack(side='left', padx=5)
        
        self.clear_btn = ttk.Button(button_frame, text="🗑️ 清空结果", command=self.clear_results)
        self.clear_btn.pack(side='left', padx=5)
        
        # 进度和状态
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill='x', pady=(10, 0))
        
        self.status_var = tk.StringVar(value="等待开始分析...")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side='left')
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.pack(side='right', fill='x', expand=True, padx=(10, 0))
        
        # 主内容区域
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # 创建笔记本控件（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True)
        
        # 结果标签页
        result_frame = ttk.Frame(notebook)
        notebook.add(result_frame, text="分析结果")
        
        # 统计信息
        stats_frame = ttk.LabelFrame(result_frame, text="统计信息", padding=10)
        stats_frame.pack(fill='x', pady=(0, 5))
        
        self.stats_text = tk.Text(stats_frame, height=4, wrap='word')
        self.stats_text.pack(fill='x')
        
        # 结果表格
        table_frame = ttk.LabelFrame(result_frame, text="候选股票", padding=10)
        table_frame.pack(fill='both', expand=True, pady=(0, 5))
        
        columns = ('股票名', '代码', '股价', 'PB', 'PE', '市值(亿)')
        self.result_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.result_tree.heading(col, text=col)
            self.result_tree.column(col, width=100)
        
        v_scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.result_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient='horizontal', command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.result_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # 日志标签页
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="日志")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD)
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
        self.log_message("应用启动成功，等待开始分析...")
        
    def log_message(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def get_realtime_quotes_sina_fixed(self):
        """从新浪财经获取实时A股行情（最终修复版）"""
        self.log_message("正在获取实时行情数据...")
        self.status_var.set("正在获取实时行情数据...")
        
        all_data = []
        for page in range(1, 100):
            try:
                url = f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page={page}&num=80&sort=code&asc=1&node=hs_a"
                response = requests.get(url, timeout=10)
                data = response.json()
                
                if not data:
                    break
                    
                all_data.extend(data)
                self.log_message(f"已获取第 {page} 页数据，累计 {len(all_data)} 只股票")
                time.sleep(0.5)
            except Exception as e:
                self.log_message(f"获取第 {page} 页失败: {e}")
                break
        
        if not all_data:
            self.log_message("❌ 无法获取实时行情数据")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        df['code'] = df['symbol'].str[2:]  # 去掉 'sz' 或 'sh' 前缀
        df['pb'] = pd.to_numeric(df['pb'], errors='coerce')
        df['per'] = pd.to_numeric(df['per'], errors='coerce')
        df['trade'] = pd.to_numeric(df['trade'], errors='coerce')
        df['mktcap'] = pd.to_numeric(df['mktcap'], errors='coerce') * 10000  # 万元转元
        
        df = df.rename(columns={
            'name': 'name',
            'pb': 'pb_ratio',
            'per': 'pe_ratio', 
            'trade': 'price',
            'mktcap': 'market_cap'
        })
        
        df = df.dropna(subset=['pb_ratio', 'price'])
        df = df[df['pb_ratio'] > 0]
        df = df[df['price'] > 0]
        
        self.log_message(f"📊 成功获取 {len(df)} 只股票的有效行情数据")
        return df[['code', 'name', 'price', 'pb_ratio', 'pe_ratio', 'market_cap']]

    def get_cigar_butt_realtime_final(self):
        """实时捡烟蒂策略（使用真实股票名称）"""
        self.log_message("🔍 开始执行捡烟蒂策略...")
        
        realtime_data = self.get_realtime_quotes_sina_fixed()
        if realtime_data.empty:
            self.log_message("❌ 获取实时行情失败")
            return pd.DataFrame(), pd.DataFrame()
        
        self.log_message(f"📊 从新浪财经获取到 {len(realtime_data)} 只股票数据")

        # 直接使用行情数据中的 name 字段，并过滤 ST/退市股
        df = realtime_data.copy()
        df = df[~df['name'].str.contains('ST|退|B股|暂停', na=False, regex=True)]
        df['code'] = df['code'].astype(str).str.zfill(6)

        # 应用筛选条件
        pb_max = float(self.pb_max_var.get())
        pe_max = float(self.pe_max_var.get())
        mcap_min = float(self.mcap_min_var.get()) * 1e8  # 转为元

        candidates = df[
            (df['pb_ratio'] > 0) & (df['pb_ratio'] <= pb_max) &
            (df['pe_ratio'] > 0) & (df['pe_ratio'] <= pe_max) &
            (df['market_cap'] > mcap_min) &
            (df['price'] > 0)
        ].copy()

        if not candidates.empty:
            result = candidates[['name', 'code', 'price', 'pb_ratio', 'pe_ratio', 'market_cap']].copy()
            result['market_cap'] = (result['market_cap'] / 1e8).round(2)  # 转亿元
            result.columns = ['股票名', '代码', '股价', 'PB', 'PE', '市值(亿)']
            result = result.sort_values('PB').reset_index(drop=True)

            self.log_message(f"\n✅ 找到 {len(result)} 只捡烟蒂候选股（PB≤{pb_max}）:")
            for _, row in result.head(10).iterrows():
                self.log_message(f"  {row['股票名']} ({row['代码']}) - PB: {row['PB']:.3f}, 价格: {row['股价']:.2f}")

            return result, df
        else:
            self.log_message("❌ 未找到符合条件的股票")
            
            lowest = df.nsmallest(20, 'pb_ratio')[['name', 'code', 'price', 'pb_ratio', 'pe_ratio', 'market_cap']].copy()
            lowest['market_cap'] = (lowest['market_cap'] / 1e8).round(2)
            lowest.columns = ['股票名', '代码', '股价', 'PB', 'PE', '市值(亿)']
            
            self.log_message(f"\n📊 PB 最低的 20 只股票:")
            for _, row in lowest.head(5).iterrows():
                self.log_message(f"  {row['股票名']} ({row['代码']}) - PB: {row['PB']:.3f}, 价格: {row['股价']:.2f}")
            
            return pd.DataFrame(), df

    def start_analysis(self):
        """开始分析"""
        self.analyze_btn.config(state='disabled')
        self.export_btn.config(state='disabled')
        self.progress.start()
        thread = threading.Thread(target=self.run_analysis)
        thread.daemon = True
        thread.start()
        
    def run_analysis(self):
        """运行分析（在新线程中）"""
        try:
            start_time = time.time()
            candidates, all_data = self.get_cigar_butt_realtime_final()
            
            if not candidates.empty:
                self.display_results(candidates, all_data)
                candidates.to_csv('cigar_butt_realtime.csv', index=False, encoding='utf-8-sig')
                self.log_message("✅ 结果已保存到 cigar_butt_realtime.csv")
                self.export_btn.config(state='normal')
            else:
                self.clear_results_table()
                self.stats_text.delete(1.0, tk.END)
                self.stats_text.insert(tk.END, "未找到符合条件的股票")
                self.log_message("未找到符合条件的股票")
            
            elapsed_time = time.time() - start_time
            self.log_message(f"⏱️ 总耗时: {elapsed_time:.2f} 秒")
            
        except Exception as e:
            self.log_message(f"❌ 分析过程中出现错误: {str(e)}")
        finally:
            self.progress.stop()
            self.root.after(0, lambda: self.analyze_btn.config(state='normal'))
            self.status_var.set("分析完成")
    
    def display_results(self, candidates, all_data):
        """显示分析结果"""
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        for _, row in candidates.iterrows():
            self.result_tree.insert('', 'end', values=(
                row['股票名'],
                row['代码'], 
                f"{row['股价']:.2f}",
                f"{row['PB']:.3f}",
                f"{row['PE']:.2f}",
                f"{row['市值(亿)']:.2f}"
            ))
        
        if not all_data.empty:
            stats = f"""总股票数: {len(all_data)}
候选股票数: {len(candidates)}
PB范围: {all_data['pb_ratio'].min():.3f} ~ {all_data['pb_ratio'].max():.3f}
PE范围: {all_data['pe_ratio'].min():.2f} ~ {all_data['pe_ratio'].max():.2f}
平均PB: {all_data['pb_ratio'].mean():.3f}
平均PE: {all_data['pe_ratio'].mean():.2f}"""
        else:
            stats = "暂无统计数据"
        
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, stats)
        self.analysis_result = candidates
        self.all_data = all_data
    
    def clear_results_table(self):
        """清空结果表格"""
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
    
    def export_results(self):
        """导出结果"""
        if self.analysis_result is None or self.analysis_result.empty:
            messagebox.showwarning("警告", "没有可导出的结果")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="保存分析结果"
        )
        
        if filename:
            try:
                self.analysis_result.to_csv(filename, index=False, encoding='utf-8-sig')
                messagebox.showinfo("成功", f"结果已保存到 {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def clear_results(self):
        """清空结果"""
        self.clear_results_table()
        self.stats_text.delete(1.0, tk.END)
        self.analysis_result = None
        self.all_data = None
        self.export_btn.config(state='disabled')
        self.log_message("结果已清空")

def main():
    root = tk.Tk()
    app = StockAnalysisApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()