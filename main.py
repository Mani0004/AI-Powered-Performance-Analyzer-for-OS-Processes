import tkinter as tk
from tkinter import ttk, messagebox
import psutil
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import deque
import numpy as np
import threading
import time

class SystemMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OS Performance Analyzer")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f0")
        
        # Configure styles for light theme
        style = ttk.Style()
        style.configure("TFrame", background="#ffffff")
        style.configure("TLabelframe", background="#ffffff", foreground="#000000")
        style.configure("TLabelframe.Label", background="#ffffff", foreground="#000000")
        style.configure("TLabel", background="#ffffff", foreground="#000000")
        style.configure("Treeview", background="#ffffff", foreground="#000000", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", background="#e1e1e1", foreground="#000000")
        style.configure("TButton", background="#007acc", foreground="#ffffff", padding=(10, 5))
        style.map("TButton",
            background=[("active", "#0066cc"), ("pressed", "#005fb8")],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")])
        
        # Configure Treeview selection colors
        style.map("Treeview",
            background=[("selected", "#007acc")],
            foreground=[("selected", "#ffffff")])
        
        # Initialize data for graphs
        self.cpu_data = deque(maxlen=30)
        self.memory_data = deque(maxlen=30)
        self.time_data = deque(maxlen=30)
        self.network_sent_data = deque(maxlen=30)
        self.network_recv_data = deque(maxlen=30)
        self.prev_net_io = psutil.net_io_counters()
        self.alert_threshold = 90  # Alert threshold for resource usage
        self.last_alert = 0  # To prevent alert spam
        
        self.setup_ui()
        self.root.attributes('-alpha', 0.0)
        self.fade_in()
        self.update_stats()
    
    def setup_ui(self):
        # Main Panel for all content
        main_panel = ttk.Frame(self.root)
        main_panel.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Top Panel for Stats and Processes
        top_panel = ttk.Frame(main_panel)
        top_panel.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create a frame for system stats and process list side by side
        top_left_frame = ttk.Frame(top_panel)
        top_left_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        top_right_frame = ttk.Frame(top_panel)
        top_right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        # System Stats Frame
        stats_frame = ttk.LabelFrame(top_left_frame, text="System Statistics", padding=10)
        stats_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create a grid layout for system stats
        # CPU Usage
        ttk.Label(stats_frame, text="CPU Usage:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.cpu_label = ttk.Label(stats_frame, text="0%")
        self.cpu_label.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # Memory Usage
        ttk.Label(stats_frame, text="Memory Usage:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.memory_label = ttk.Label(stats_frame, text="0%")
        self.memory_label.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # Disk Usage
        ttk.Label(stats_frame, text="Disk Usage:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.disk_label = ttk.Label(stats_frame, text="0%")
        self.disk_label.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Network Usage
        ttk.Label(stats_frame, text="Network Usage:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.network_label = ttk.Label(stats_frame, text="↑0 MB/s ↓0 MB/s")
        self.network_label.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        
        # Temperature
        ttk.Label(stats_frame, text="CPU Temperature:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.temp_label = ttk.Label(stats_frame, text="N/A")
        self.temp_label.grid(row=4, column=1, sticky="w", padx=5, pady=5)
        
        # Process Control Buttons
        control_frame = ttk.Frame(stats_frame)
        control_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=5)
        
        ttk.Button(control_frame, text="Increase Priority", command=lambda: self.modify_priority(increase=True)).grid(row=0, column=0, padx=2)
        ttk.Button(control_frame, text="Decrease Priority", command=lambda: self.modify_priority(increase=False)).grid(row=0, column=1, padx=2)
        
        # Process List Frame
        process_frame = ttk.LabelFrame(top_right_frame, text="Top 5 Processes", padding=10)
        process_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Process Treeview
        self.process_tree = ttk.Treeview(process_frame, columns=("Name", "PID", "CPU%", "Memory%"), show="headings", style="Custom.Treeview")
        self.process_tree.heading("Name", text="Name")
        self.process_tree.heading("PID", text="PID")
        self.process_tree.heading("CPU%", text="CPU%")
        self.process_tree.heading("Memory%", text="Memory%")
        style = ttk.Style()
        
        style.configure("Custom.Treeview", font=("Arial", 12))
        self.process_tree.pack(fill="both", expand=True)
        
        # Bottom Panel for Graphs
        bottom_panel = ttk.Frame(main_panel)
        bottom_panel.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Graphs Frame
        graphs_frame = ttk.LabelFrame(bottom_panel, text="Performance Graphs", padding=10)
        graphs_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create matplotlib figure for all metrics with adjusted size
        self.fig = Figure(figsize=(12, 4), dpi=100)
        gs = self.fig.add_gridspec(3, 1, hspace=0.4)
        self.ax1 = self.fig.add_subplot(gs[0])
        self.ax2 = self.fig.add_subplot(gs[1])
        self.ax3 = self.fig.add_subplot(gs[2])
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=graphs_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def modify_priority(self, increase):
        selected = self.process_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process first")
            return

        item = self.process_tree.item(selected[0])
        pid = int(item['values'][1])
        try:
            p = psutil.Process(pid)
            if increase and p.nice() > -20:  # Linux/Unix priority range
                p.nice(p.nice() - 1)
            elif not increase and p.nice() < 19:
                p.nice(p.nice() + 1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            messagebox.showerror("Error", "Cannot modify process priority")
        selected = self.process_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process first")
            return
        
        item = self.process_tree.item(selected[0])
        pid = int(item['values'][1])
        try:
            p = psutil.Process(pid)
            if increase and p.nice() > -20:  # Linux/Unix priority range
                p.nice(p.nice() - 1)
            elif not increase and p.nice() < 19:
                p.nice(p.nice() + 1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            messagebox.showerror("Error", "Cannot modify process priority")
    
    def decrease_priority(self):
        selected = self.process_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process first")
            return
        
        item = self.process_tree.item(selected[0])
        pid = int(item['values'][1])
        try:
            p = psutil.Process(pid)
            if p.nice() < 19:  # Linux/Unix priority range
                p.nice(p.nice() + 1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            messagebox.showerror("Error", "Cannot modify process priority")
    
    def check_alerts(self, cpu_percent, memory_percent):
        current_time = time.time()
        if current_time - self.last_alert < 60:  # Only alert once per minute
            return
        
        if cpu_percent > self.alert_threshold:
            messagebox.showwarning("High CPU Usage", f"CPU usage is at {cpu_percent}%!")
            self.last_alert = current_time
        elif memory_percent > self.alert_threshold:
            messagebox.showwarning("High Memory Usage", f"Memory usage is at {memory_percent}%!")
            self.last_alert = current_time
    
    def fade_in(self):
        alpha = self.root.attributes('-alpha')
        if alpha < 1.0:
            alpha += 0.05
            self.root.attributes('-alpha', alpha)
            self.root.after(50, self.fade_in)

    def update_stats(self):
        # Update CPU Usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.cpu_label.config(text=f"CPU Usage: {cpu_percent}%")
        
        # Update Memory Usage
        memory = psutil.virtual_memory()
        self.memory_label.config(text=f"Memory Usage: {memory.percent}%")
        
        # Update Disk Usage
        disk = psutil.disk_usage('/')
        self.disk_label.config(text=f"Disk Usage: {disk.percent}%")
        
        # Update Process List
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort by CPU usage and get top 5
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        top_processes = processes[:10]
        
        # Update Process List
        existing_pids = {self.process_tree.item(item)['values'][1]: item for item in self.process_tree.get_children()}
        
        for proc in top_processes:
            pid = proc['pid']
            if pid in existing_pids:
                self.process_tree.item(existing_pids[pid], values=(
                    proc['name'],
                    proc['pid'],
                    f"{proc['cpu_percent']:.1f}",
                    f"{proc['memory_percent']:.1f}"
                ))
            else:
                self.process_tree.insert("", "end", values=(
                    proc['name'],
                    proc['pid'],
                    f"{proc['cpu_percent']:.1f}",
                    f"{proc['memory_percent']:.1f}"
                ))
        
        # Remove processes no longer in the top list
        for pid, item in existing_pids.items():
            if pid not in [proc['pid'] for proc in top_processes]:
                self.process_tree.delete(item)
        
        # Update Network Usage
        net_io = psutil.net_io_counters()
        sent = (net_io.bytes_sent - self.prev_net_io.bytes_sent) / 1024 / 1024  # MB/s
        recv = (net_io.bytes_recv - self.prev_net_io.bytes_recv) / 1024 / 1024  # MB/s
        self.prev_net_io = net_io
        self.network_label.config(text=f"Network: ↑{sent:.1f} MB/s ↓{recv:.1f} MB/s")
        
        # Update Temperature (if available)
        try:
            temps = psutil.sensors_temperatures()
            if temps and 'coretemp' in temps:
                temp = temps['coretemp'][0].current
                self.temp_label.config(text=f"CPU Temperature: {temp}°C")
        except (AttributeError, KeyError):
            self.temp_label.config(text="CPU Temperature: N/A")
        
        # Check for alerts
        self.check_alerts(cpu_percent, memory.percent)
        
        # Update graphs
        current_time = datetime.now().strftime('%H:%M:%S')
        self.cpu_data.append(cpu_percent)
        self.memory_data.append(memory.percent)
        self.time_data.append(current_time)
        self.network_sent_data.append(sent)
        self.network_recv_data.append(recv)
        
        # Clear previous plots
        self.ax1.clear()
        self.ax2.clear()
        
        # Plot CPU usage
        self.ax1.plot(list(range(len(self.cpu_data))), list(self.cpu_data), 'b-', label='CPU Usage', alpha=0.8, linewidth=2)
        self.ax1.set_title('CPU Usage Over Time', fontdict={'fontsize': 14, 'fontweight': 'bold', 'color': 'blue'})
        self.ax1.set_ylim(0, 100)
        self.ax1.grid(True, linestyle='--', alpha=0.7)
        self.ax1.tick_params(axis='x', labelbottom=False)
        
        # Plot Memory usage
        self.ax2.plot(list(range(len(self.memory_data))), list(self.memory_data), 'r-', label='Memory Usage', alpha=0.8, linewidth=2)
        self.ax2.set_title('Memory Usage Over Time', fontdict={'fontsize': 14, 'fontweight': 'bold', 'color': 'red'})
        self.ax2.set_ylim(0, 100)
        self.ax2.grid(True, linestyle='--', alpha=0.7)
        self.ax2.tick_params(axis='x', labelbottom=False)
        
        # Plot Network usage with simplified legend
        self.ax3.plot(list(self.time_data), list(self.network_sent_data), 'g-', label='Upload', alpha=0.8, linewidth=2)
        self.ax3.plot(list(self.time_data), list(self.network_recv_data), 'y-', label='Download', alpha=0.8, linewidth=2)
        self.ax3.set_title('Network Usage Over Time (MB/s)', fontdict={'fontsize': 14, 'fontweight': 'bold', 'color': 'green'})
        self.ax3.grid(True, linestyle='--', alpha=0.7)
        self.ax3.tick_params(axis='x', rotation=45, labelsize=10)
        self.ax3.legend(loc='upper right', labels=['Upload', 'Download'])
        
        # Adjust layout and draw
        self.fig.tight_layout()
        self.canvas.draw()
        
        
        # Schedule next update
        self.root.after(1000, self.update_stats)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SystemMonitor()
    app.run()
