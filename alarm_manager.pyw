import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import sqlite3
from datetime import datetime, timedelta
import threading
import time
import pystray
from PIL import Image
import os
import winreg
import sys

class AlarmManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("闹钟提醒管理器")
        self.root.geometry("600x400")
        
        # 程序路径
        self.app_path = os.path.abspath(sys.argv[0])
        
        # 初始化数据库
        self.init_database()
        
        # 创建GUI组件
        self.create_widgets()
        
        # 创建托盘图标
        self.create_tray_icon()
        
        # 绑定窗口关闭事件
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        # 启动闹钟检查线程
        self.check_thread = threading.Thread(target=self.check_alarms, daemon=True)
        self.check_thread.start()
        
    def init_database(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect('alarms.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS alarms
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     title TEXT NOT NULL,
                     datetime TEXT NOT NULL,
                     status TEXT DEFAULT 'active')''')
        conn.commit()
        conn.close()
        
    def create_widgets(self):
        """创建GUI组件"""
        # 创建左侧添加闹钟区域
        left_frame = ttk.LabelFrame(self.root, text="添加新闹钟", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标题输入
        ttk.Label(left_frame, text="提醒标题:").pack(fill=tk.X, pady=2)
        self.title_entry = ttk.Entry(left_frame)
        self.title_entry.pack(fill=tk.X, pady=2)
        
        # 快速设置区域
        quick_frame = ttk.LabelFrame(left_frame, text="快速设置", padding=5)
        quick_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(quick_frame, text="分钟后提醒:").pack(side=tk.LEFT, padx=2)
        self.minutes_entry = ttk.Entry(quick_frame, width=8)
        self.minutes_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="设置", command=self.add_quick_alarm).pack(side=tk.LEFT, padx=2)
        
        # 日期选择
        ttk.Label(left_frame, text="选择日期:").pack(fill=tk.X, pady=2)
        self.date_picker = DateEntry(left_frame, width=12, background='darkblue',
                                   foreground='white', borderwidth=2)
        self.date_picker.pack(fill=tk.X, pady=2)
        
        # 时间选择
        ttk.Label(left_frame, text="选择时间 (HH:MM):").pack(fill=tk.X, pady=2)
        time_frame = ttk.Frame(left_frame)
        time_frame.pack(fill=tk.X, pady=2)
        
        self.hour_spinbox = ttk.Spinbox(time_frame, from_=0, to=23, width=5)
        self.hour_spinbox.pack(side=tk.LEFT, padx=2)
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        self.minute_spinbox = ttk.Spinbox(time_frame, from_=0, to=59, width=5)
        self.minute_spinbox.pack(side=tk.LEFT, padx=2)
        
        # 添加按钮
        ttk.Button(left_frame, text="添加闹钟", command=self.add_alarm).pack(fill=tk.X, pady=10)
        
        # 创建右侧闹钟列表区域
        right_frame = ttk.LabelFrame(self.root, text="闹钟列表", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建树形视图显示闹钟列表
        self.tree = ttk.Treeview(right_frame, columns=('ID', '标题', '时间', '状态'), show='headings')
        self.tree.heading('ID', text='ID')
        self.tree.heading('标题', text='标题')
        self.tree.heading('时间', text='时间')
        self.tree.heading('状态', text='状态')
        
        # 设置列宽
        self.tree.column('ID', width=50)
        self.tree.column('标题', width=100)
        self.tree.column('时间', width=150)
        self.tree.column('状态', width=70)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # 添加删除按钮
        ttk.Button(right_frame, text="删除选中", command=self.delete_alarm).pack(fill=tk.X, pady=5)
        
        # 刷新闹钟列表
        self.refresh_alarm_list()
        
    def create_tray_icon(self):
        """创建托盘图标"""
        # 加载图标
        try:
            # 尝试从打包后的路径获取图标
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_path, 'icon.png')
            image = Image.open(icon_path)
        except Exception as e:
            # 如果加载失败，创建一个简单的默认图标
            image = Image.new('RGB', (32, 32), color='red')
        
        # 创建托盘菜单
        menu = (
            pystray.MenuItem("显示主窗口", self.show_window),
            pystray.MenuItem("开机自启动", self.toggle_autostart, checked=lambda item: self.is_autostart_enabled()),
            pystray.MenuItem("退出", self.quit_window)
        )
        
        # 创建托盘图标
        self.icon = pystray.Icon("alarm_manager", image, "闹钟提醒", menu)
        
        # 启动托盘图标
        threading.Thread(target=self.icon.run, daemon=True).start()
        
    def is_autostart_enabled(self):
        """检查是否已启用开机自启动"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                value, _ = winreg.QueryValueEx(key, "AlarmManager")
                return value == f'"{self.app_path}"'
            except WindowsError:
                return False
            finally:
                winreg.CloseKey(key)
        except WindowsError:
            return False
            
    def toggle_autostart(self, icon, item):
        """切换开机自启动状态"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
            )
            
            if self.is_autostart_enabled():
                # 禁用自启动
                winreg.DeleteValue(key, "AlarmManager")
                messagebox.showinfo("提示", "已禁用开机自启动")
            else:
                # 启用自启动
                winreg.SetValueEx(
                    key,
                    "AlarmManager",
                    0,
                    winreg.REG_SZ,
                    f'"{self.app_path}"'
                )
                messagebox.showinfo("提示", "已启用开机自启动")
                
            winreg.CloseKey(key)
            # 更新菜单项状态
            item.checked = not item.checked
            
        except Exception as e:
            messagebox.showerror("错误", f"设置开机自启动失败: {str(e)}")
            
    def show_window(self, icon=None):
        """显示主窗口"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        
    def hide_window(self):
        """隐藏主窗口"""
        self.root.withdraw()
        
    def quit_window(self, icon=None):
        """退出程序"""
        self.icon.stop()
        self.root.destroy()
        
    def add_quick_alarm(self):
        """添加快速闹钟（N分钟后提醒）"""
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showerror("错误", "请输入提醒标题")
            return
            
        try:
            minutes = int(self.minutes_entry.get())
            if minutes <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "请输入有效的分钟数")
            return
            
        alarm_time = datetime.now() + timedelta(minutes=minutes)
        
        conn = sqlite3.connect('alarms.db')
        c = conn.cursor()
        c.execute("INSERT INTO alarms (title, datetime) VALUES (?, ?)",
                 (title, alarm_time.strftime('%Y-%m-%d %H:%M')))
        conn.commit()
        conn.close()
        
        self.refresh_alarm_list()
        self.title_entry.delete(0, tk.END)
        self.minutes_entry.delete(0, tk.END)
        
    def add_alarm(self):
        """添加新闹钟"""
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showerror("错误", "请输入提醒标题")
            return
            
        date = self.date_picker.get_date()
        hour = self.hour_spinbox.get()
        minute = self.minute_spinbox.get()
        
        try:
            hour = int(hour)
            minute = int(minute)
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "请输入有效的时间")
            return
            
        alarm_time = datetime.combine(date, datetime.min.time().replace(hour=hour, minute=minute))
        
        if alarm_time < datetime.now():
            messagebox.showerror("错误", "不能设置过去的时间")
            return
            
        conn = sqlite3.connect('alarms.db')
        c = conn.cursor()
        c.execute("INSERT INTO alarms (title, datetime) VALUES (?, ?)",
                 (title, alarm_time.strftime('%Y-%m-%d %H:%M')))
        conn.commit()
        conn.close()
        
        self.refresh_alarm_list()
        self.title_entry.delete(0, tk.END)
        
    def delete_alarm(self):
        """删除选中的闹钟"""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择要删除的闹钟")
            return
            
        if messagebox.askyesno("确认", "确定要删除选中的闹钟吗？"):
            conn = sqlite3.connect('alarms.db')
            c = conn.cursor()
            for item in selected_item:
                alarm_id = self.tree.item(item)['values'][0]
                c.execute("DELETE FROM alarms WHERE id=?", (alarm_id,))
            conn.commit()
            conn.close()
            self.refresh_alarm_list()
            
    def refresh_alarm_list(self):
        """刷新闹钟列表"""
        # 清空现有项目
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # 从数据库加载闹钟
        conn = sqlite3.connect('alarms.db')
        c = conn.cursor()
        c.execute("SELECT * FROM alarms ORDER BY datetime")
        alarms = c.fetchall()
        conn.close()
        
        # 设置标签样式
        self.tree.tag_configure('expired', foreground='gray')
        self.tree.tag_configure('triggered', foreground='red')
        self.tree.tag_configure('active', foreground='green')
        
        # 显示闹钟列表
        current_time = datetime.now()
        for alarm in alarms:
            alarm_id, title, alarm_time_str, status = alarm
            
            # 确定闹钟状态和标签
            if status == 'triggered':
                tag = 'triggered'
                status_text = '已提醒'
            elif alarm_time_str < current_time.strftime('%Y-%m-%d %H:%M'):
                tag = 'expired'
                status_text = '已过期'
                # 更新数据库中的状态
                conn = sqlite3.connect('alarms.db')
                c = conn.cursor()
                c.execute("UPDATE alarms SET status='expired' WHERE id=? AND status='active'", (alarm_id,))
                conn.commit()
                conn.close()
            else:
                tag = 'active'
                status_text = '等待中'
            
            self.tree.insert('', tk.END, values=(alarm_id, title, alarm_time_str, status_text), tags=(tag,))
            
    def check_alarms(self):
        """检查闹钟是否到期"""
        while True:
            conn = sqlite3.connect('alarms.db')
            c = conn.cursor()
            c.execute("SELECT * FROM alarms WHERE status='active'")
            alarms = c.fetchall()
            
            current_time = datetime.now()
            for alarm in alarms:
                alarm_time = datetime.strptime(alarm[2], '%Y-%m-%d %H:%M')
                if current_time >= alarm_time:
                    # 更新状态为已触发
                    c.execute("UPDATE alarms SET status='triggered' WHERE id=?", (alarm[0],))
                    # 显示提醒
                    self.show_alarm(alarm[1])
                    
            conn.commit()
            conn.close()
            # 刷新闹钟列表以更新显示状态
            self.root.after(0, self.refresh_alarm_list)
            time.sleep(30)  # 每30秒检查一次
            
    def show_alarm(self, title):
        """显示闹钟提醒"""
        def show_message():
            # 创建置顶提醒窗口
            popup = tk.Toplevel(self.root)
            popup.title("时间到了!")
            popup.geometry("300x150")
            # 设置窗口置顶
            popup.attributes('-topmost', True)
            # 窗口居中
            popup.geometry("+%d+%d" % (
                self.root.winfo_screenwidth() // 2 - 150,
                self.root.winfo_screenheight() // 2 - 75
            ))
            
            # 添加提醒内容
            message_frame = ttk.Frame(popup, padding="20")
            message_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(message_frame, text="提醒事项:", font=('Arial', 12, 'bold')).pack(pady=5)
            ttk.Label(message_frame, text=title, font=('Arial', 11)).pack(pady=5)
            
            # 确认按钮
            ttk.Button(message_frame, text="确定", command=popup.destroy).pack(pady=10)
            
            # 播放提示音
            popup.bell()
            
        self.root.after(0, show_message)
        
    def run(self):
        """运行程序"""
        # 初始隐藏窗口
        self.root.withdraw()
        self.root.mainloop()

if __name__ == "__main__":
    app = AlarmManager()
    app.run()
