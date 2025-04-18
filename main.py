import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import psutil
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import deque
import numpy as np
import threading
import time
from google import genai  # Added for Gemini API integration
import os
import sys
from tkinter.font import Font

# Gemini API configuration
GEMINI_API_KEY = "AIzaSyDQyRfpXK3lYkm6XKNv_QisQJ5jZ0qfH44"

class SystemMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OS Performance Analyzer")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        self.root.configure(bg="#f5f5f5")
        
        # Set app icon if possible
        try:
            if os.name == 'nt':  # For Windows
                self.root.iconbitmap(default="")
        except:
            pass
            
        # Initialize Gemini API client
        self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Gemini analysis results
        self.gemini_result = None
        self.gemini_analyzing = False
        
        # Define custom fonts
        self.header_font = Font(family="Segoe UI", size=11, weight="bold")
        self.label_font = Font(family="Segoe UI", size=10)
        self.value_font = Font(family="Segoe UI", size=10)
        self.title_font = Font(family="Segoe UI", size=12, weight="bold")
        
        # Define color scheme
        self.bg_color = "#f5f5f5"
        self.frame_bg = "#ffffff"
        self.accent_color = "#0078d7"
        self.text_color = "#333333"
        self.critical_color = "#d83b01"
        self.warning_color = "#ffaa44"
        self.safe_color = "#107c10"
        
        # Configure styles for modern theme
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure frames
        style.configure("TFrame", background=self.frame_bg)
        style.configure("MainFrame.TFrame", background=self.bg_color)
        
        # Configure label frames
        style.configure("TLabelframe", background=self.frame_bg, bordercolor=self.accent_color)
        style.configure("TLabelframe.Label", 
                       background=self.frame_bg, 
                       foreground=self.accent_color,
                       font=self.header_font)
        
        # Configure labels
        style.configure("TLabel", 
                       background=self.frame_bg, 
                       foreground=self.text_color,
                       font=self.label_font)
        
        style.configure("Header.TLabel", 
                       background=self.frame_bg, 
                       foreground=self.text_color,
                       font=self.header_font)
                       
        style.configure("Value.TLabel", 
                       background=self.frame_bg, 
                       foreground=self.accent_color,
                       font=self.value_font)
        
        # Configure Treeview                
        style.configure("Treeview", 
                       background=self.frame_bg, 
                       foreground=self.text_color, 
                       fieldbackground=self.frame_bg,
                       font=self.value_font,
                       rowheight=25)
                       
        style.configure("Treeview.Heading", 
                       background=self.accent_color, 
                       foreground="white",
                       font=self.header_font)
                       
        # Configure Treeview selection colors
        style.map("Treeview",
            background=[("selected", self.accent_color)],
            foreground=[("selected", "white")])
        
        # Configure buttons
        style.configure("TButton", 
                       background=self.accent_color, 
                       foreground="white", 
                       font=self.label_font,
                       padding=(10, 5))
                       
        style.map("TButton",
            background=[("active", "#005a9e"), ("pressed", "#004578")],
            foreground=[("active", "white"), ("pressed", "white")])
            
        style.configure("Accent.TButton", 
                       background=self.accent_color, 
                       foreground="white", 
                       font=self.header_font,
                       padding=(15, 8))
                       
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
        self.update_stats()
    
    def setup_ui(self):
        # Main Panel for all content (with background color)
        main_panel = ttk.Frame(self.root, style="MainFrame.TFrame")
        main_panel.pack(fill="both", expand=True, padx=10, pady=10)
        
        # App header with title
        header_frame = ttk.Frame(main_panel, style="MainFrame.TFrame")
        header_frame.pack(fill="x", padx=5, pady=(0, 10))
        
        header_label = ttk.Label(
            header_frame, 
            text="OS Performance Analyzer", 
            font=self.title_font,
            foreground=self.accent_color,
            background=self.bg_color
        )
        header_label.pack(side="left", padx=5)
        
        # Tab-like interface
        notebook = ttk.Notebook(main_panel)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Dashboard tab
        dashboard_frame = ttk.Frame(notebook)
        notebook.add(dashboard_frame, text="Dashboard")
        
        # Advanced analysis tab
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="AI Analysis")
        
        # === DASHBOARD TAB CONTENT ===
        # Create a vertical layout with graphs getting more space
        dashboard_paned = ttk.PanedWindow(dashboard_frame, orient=tk.VERTICAL)
        dashboard_paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Top section for metrics and process info (smaller)
        top_section = ttk.Frame(dashboard_paned)
        dashboard_paned.add(top_section, weight=40)
        
        # Bottom section for sexy graphs (larger)
        bottom_section = ttk.Frame(dashboard_paned)
        dashboard_paned.add(bottom_section, weight=60)
        
        # Top panel split into 3 sections for metrics
        metrics_frame = ttk.Frame(top_section)
        metrics_frame.pack(fill="x", expand=False, padx=5, pady=5)
        
        # CPU usage card
        cpu_frame = ttk.LabelFrame(metrics_frame, text="CPU Usage", padding=10)
        cpu_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        self.cpu_value = ttk.Label(cpu_frame, text="0%", style="Value.TLabel", font=("Segoe UI", 20))
        self.cpu_value.pack(pady=5)
        
        # Memory usage card
        memory_frame = ttk.LabelFrame(metrics_frame, text="Memory Usage", padding=10)
        memory_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        self.memory_value = ttk.Label(memory_frame, text="0%", style="Value.TLabel", font=("Segoe UI", 20))
        self.memory_value.pack(pady=5)
        
        # Disk usage card
        disk_frame = ttk.LabelFrame(metrics_frame, text="Disk Usage", padding=10)
        disk_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        
        self.disk_value = ttk.Label(disk_frame, text="0%", style="Value.TLabel", font=("Segoe UI", 20))
        self.disk_value.pack(pady=5)
        
        # Grid configuration
        metrics_frame.columnconfigure(0, weight=1)
        metrics_frame.columnconfigure(1, weight=1)
        metrics_frame.columnconfigure(2, weight=1)
        
        # Middle section with detailed stats and processes - more compact now
        mid_frame = ttk.Frame(top_section)
        mid_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # System stats frame (left side) - more compact
        stats_frame = ttk.LabelFrame(mid_frame, text="System Details", padding=5)
        stats_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # System stats table
        stats_table = ttk.Frame(stats_frame)
        stats_table.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Network Usage
        ttk.Label(stats_table, text="Network:", style="Header.TLabel").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.network_label = ttk.Label(stats_table, text="↑0 MB/s ↓0 MB/s", style="Value.TLabel")
        self.network_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        # CPU Temperature
        ttk.Label(stats_table, text="CPU Temperature:", style="Header.TLabel").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.temp_label = ttk.Label(stats_table, text="N/A", style="Value.TLabel")
        self.temp_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        # System Uptime
        ttk.Label(stats_table, text="System Uptime:", style="Header.TLabel").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.uptime_label = ttk.Label(stats_table, text="0 days, 0 hours", style="Value.TLabel")
        self.uptime_label.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        # Process control section - more compact
        control_frame = ttk.LabelFrame(stats_frame, text="Process Control", padding=5)
        control_frame.pack(fill="x", expand=False, padx=5, pady=5)
        
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(buttons_frame, text="Increase Priority", command=self.increase_priority).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="Decrease Priority", command=self.decrease_priority).pack(side="left", padx=5)
        
        # Process list frame (right side)
        process_frame = ttk.LabelFrame(mid_frame, text="Top Processes", padding=5)
        process_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        # Process Treeview with scrollbar
        process_container = ttk.Frame(process_frame)
        process_container.pack(fill="both", expand=True)
        
        # Add scrollbars
        process_scroll_y = ttk.Scrollbar(process_container, orient="vertical")
        process_scroll_y.pack(side="right", fill="y")
        
        process_scroll_x = ttk.Scrollbar(process_container, orient="horizontal")
        process_scroll_x.pack(side="bottom", fill="x")
        
        # Process Treeview
        self.process_tree = ttk.Treeview(
            process_container,
            columns=("Name", "PID", "CPU%", "Memory%", "Status"),
            show="headings",
            selectmode="browse",
            yscrollcommand=process_scroll_y.set,
            xscrollcommand=process_scroll_x.set
        )
        
        # Configure scrollbars
        process_scroll_y.config(command=self.process_tree.yview)
        process_scroll_x.config(command=self.process_tree.xview)
        
        # Configure columns
        self.process_tree.heading("Name", text="Process Name")
        self.process_tree.heading("PID", text="PID")
        self.process_tree.heading("CPU%", text="CPU %")
        self.process_tree.heading("Memory%", text="Memory %")
        self.process_tree.heading("Status", text="Status")
        
        # Set column widths
        self.process_tree.column("Name", width=150, minwidth=100)
        self.process_tree.column("PID", width=70, minwidth=50)
        self.process_tree.column("CPU%", width=70, minwidth=50)
        self.process_tree.column("Memory%", width=80, minwidth=70)
        self.process_tree.column("Status", width=100, minwidth=80)
        
        self.process_tree.pack(fill="both", expand=True)
        
        # ENHANCED SEXY GRAPHS SECTION - now with much more space
        graphs_frame = ttk.LabelFrame(bottom_section, text="Performance Graphs", padding=10)
        graphs_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create matplotlib figure for all metrics with adjusted size and more sexy styling
        self.fig = Figure(figsize=(12, 6), dpi=100, facecolor=self.frame_bg)
        self.fig.subplots_adjust(left=0.05, right=0.98, top=0.92, bottom=0.1, hspace=0.3)
        
        # Create a more attractive grid layout for the graphs
        gs = self.fig.add_gridspec(3, 1, hspace=0.3)
        self.ax1 = self.fig.add_subplot(gs[0])
        self.ax2 = self.fig.add_subplot(gs[1])
        self.ax3 = self.fig.add_subplot(gs[2])
        
        # Enhanced styling for sexier plots
        for ax in [self.ax1, self.ax2, self.ax3]:
            ax.set_facecolor("#f0f5fa")  # Lighter, more attractive background
            ax.grid(True, linestyle="-", alpha=0.3, color="#cccccc")
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_color('#dddddd')
            ax.spines['left'].set_color('#dddddd')
            ax.tick_params(axis='both', colors="#555555", labelsize=9)
            
        # Set titles and labels with more attractive formatting
        title_style = {'fontsize': 11, 'fontweight': 'bold', 'color': '#333333'}
        self.ax1.set_title("CPU Usage (%)", **title_style)
        self.ax2.set_title("Memory Usage (%)", **title_style)
        self.ax3.set_title("Network Usage (MB/s)", **title_style)
        
        # Create canvas with correct background for sexy graphs
        self.canvas = FigureCanvasTkAgg(self.fig, master=graphs_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # === ANALYSIS TAB CONTENT ===
        analysis_header = ttk.Frame(analysis_frame)
        analysis_header.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(
            analysis_header,
            text="Gemini AI Process Analysis",
            font=self.header_font,
            style="Header.TLabel"
        ).pack(anchor="w")
        
        ttk.Label(
            analysis_header,
            text="Get AI insights about your running processes and recommendations on which ones can be safely closed",
            wraplength=800
        ).pack(anchor="w", pady=5)
        
        # Gemini Results Section
        gemini_container = ttk.Frame(analysis_frame)
        gemini_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Results box with scrollbars
        results_container = ttk.Frame(gemini_container)
        results_container.pack(fill="both", expand=True, padx=0, pady=5)
        
        results_scroll_y = ttk.Scrollbar(results_container, orient="vertical")
        results_scroll_y.pack(side="right", fill="y")
        
        results_scroll_x = ttk.Scrollbar(results_container, orient="horizontal")
        results_scroll_x.pack(side="bottom", fill="x")
        
        # Use scrolledtext widget for better text handling
        self.gemini_results_text = scrolledtext.ScrolledText(
            results_container,
            wrap="word",
            font=("Segoe UI", 10),
            bg=self.frame_bg,
            fg=self.text_color,
            height=20,
            bd=1,
            highlightthickness=0
        )
        self.gemini_results_text.pack(fill="both", expand=True)
        
        # Connect scrollbars
        self.gemini_results_text.config(
            yscrollcommand=results_scroll_y.set,
            xscrollcommand=results_scroll_x.set
        )
        results_scroll_y.config(command=self.gemini_results_text.yview)
        results_scroll_x.config(command=self.gemini_results_text.xview)
        
        # Set initial text
        self.gemini_results_text.insert(tk.END, "Click 'Analyze Processes' to get AI insights about your running processes.")
        self.gemini_results_text.config(state="disabled")
        
        # Analysis button with improved styling
        button_frame = ttk.Frame(analysis_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        analyze_button = ttk.Button(
            button_frame,
            text="Analyze Processes",
            command=self.analyze_processes_with_gemini,
            style="Accent.TButton"
        )
        analyze_button.pack(side="left", padx=5, pady=5)
        
        # Add a progress indicator
        self.analysis_status = ttk.Label(
            button_frame,
            text="",
            style="Value.TLabel"
        )
        self.analysis_status.pack(side="left", padx=10, pady=5)
    
    def increase_priority(self):
        selected = self.process_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process first")
            return
        
        item = self.process_tree.item(selected[0])
        pid = int(item['values'][1])
        try:
            p = psutil.Process(pid)
            if p.nice() > -20:  # Linux/Unix priority range
                p.nice(p.nice() - 1)
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
    
    def update_stats(self):
        # Update CPU Usage
        cpu_percent = psutil.cpu_percent(interval=0.5)
        self.cpu_value.config(text=f"{cpu_percent:.1f}%")
        
        # Update color based on usage
        cpu_color = self.safe_color
        if cpu_percent > 80:
            cpu_color = self.critical_color
        elif cpu_percent > 50:
            cpu_color = self.warning_color
        self.cpu_value.config(foreground=cpu_color)
        
        # Update Memory Usage
        memory = psutil.virtual_memory()
        self.memory_value.config(text=f"{memory.percent:.1f}%")
        
        # Update color based on usage
        mem_color = self.safe_color
        if memory.percent > 80:
            mem_color = self.critical_color
        elif memory.percent > 60:
            mem_color = self.warning_color
        self.memory_value.config(foreground=mem_color)
        
        # Update Disk Usage
        disk = psutil.disk_usage('/')
        self.disk_value.config(text=f"{disk.percent:.1f}%")
        
        # Update color based on usage
        disk_color = self.safe_color
        if disk.percent > 90:
            disk_color = self.critical_color
        elif disk.percent > 70:
            disk_color = self.warning_color
        self.disk_value.config(foreground=disk_color)
        
        # Update System Uptime
        uptime_seconds = time.time() - psutil.boot_time()
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_text = f"{int(days)} days, {int(hours)} hours, {int(minutes)} min"
        if hasattr(self, 'uptime_label'):
            self.uptime_label.config(text=uptime_text)
        
        # Update Process List
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                pinfo = proc.info
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort by CPU usage and get top processes
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        top_processes = processes[:10]  # Show more processes
        
        # Clear existing items
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)
        
        # Add new items
        for proc in top_processes:
            # Only add processes with some activity
            if proc['cpu_percent'] > 0 or proc['memory_percent'] > 0:
                self.process_tree.insert("", "end", values=(
                    proc['name'],
                    proc['pid'],
                    f"{proc['cpu_percent']:.1f}",
                    f"{proc['memory_percent']:.1f}",
                    proc['status']
                ))
        
        # Update Network Usage
        net_io = psutil.net_io_counters()
        sent = (net_io.bytes_sent - self.prev_net_io.bytes_sent) / 1024 / 1024  # MB/s
        recv = (net_io.bytes_recv - self.prev_net_io.bytes_recv) / 1024 / 1024  # MB/s
        self.prev_net_io = net_io
        self.network_label.config(text=f"↑{sent:.2f} MB/s ↓{recv:.2f} MB/s")
        
        # Update Temperature (if available)
        try:
            temps = psutil.sensors_temperatures()
            if temps and 'coretemp' in temps:
                temp = temps['coretemp'][0].current
                self.temp_label.config(text=f"{temp}°C")
            elif temps:
                # Try to find any temperature reading
                for sensor_name in temps:
                    if temps[sensor_name]:
                        temp = temps[sensor_name][0].current
                        self.temp_label.config(text=f"{temp}°C")
                        break
        except (AttributeError, KeyError):
            self.temp_label.config(text="N/A")
        
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
        self.ax3.clear()
        
        # Enhanced sexy styling for plots
        for ax in [self.ax1, self.ax2, self.ax3]:
            # Use a gradient background for more visual appeal
            ax.set_facecolor("#f8faff")
            ax.grid(True, linestyle="-", alpha=0.2, color="#bbbbbb")
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_color('#dddddd')
            ax.spines['left'].set_color('#dddddd')
            ax.tick_params(axis='both', colors="#555555", labelsize=9)
            # Add subtle horizontal lines
            ax.yaxis.grid(True, linestyle='-', alpha=0.1, color='#888888')
            # Add padding around the graph for breathing room
            ax.margins(x=0.01, y=0.1)
        
        # Convert lists for smoother plotting
        time_indices = np.arange(len(self.time_data))
        
        # Plot CPU usage with sexier styling
        cpu_color = '#0078d7'
        cpu_gradient = [(0, '#cce6ff'), (1, cpu_color)]  # Light blue to accent color
        
        # Create gradient fill using imshow
        cpu_ymax = max(100, max(self.cpu_data) * 1.1 if self.cpu_data else 100)
        if self.cpu_data:
            # Smooth the data a bit for a nicer curve
            data_array = np.array(list(self.cpu_data))
            if len(data_array) > 3:
                # Smoother line
                self.ax1.plot(
                    time_indices, 
                    data_array, 
                    color=cpu_color, 
                    linewidth=3, 
                    marker='o', 
                    markersize=4,
                    alpha=0.9,
                    markerfacecolor='white',
                    markeredgecolor=cpu_color,
                    markeredgewidth=1,
                    zorder=5
                )
                # Gradient fill below the line
                self.ax1.fill_between(
                    time_indices, 
                    data_array,
                    alpha=0.3,
                    color=cpu_color,
                    linewidth=0,
                    zorder=4
                )
                
                # Add shadow effect to line
                self.ax1.plot(
                    time_indices, 
                    data_array, 
                    color='#000000', 
                    linewidth=4,
                    alpha=0.05,
                    zorder=3
                )
            
        self.ax1.set_ylim(0, cpu_ymax)
        self.ax1.set_title("CPU Usage (%)", fontsize=11, fontweight='bold', color="#333333")
        
        # Plot Memory usage with sexy styling
        memory_color = '#e81123'
        if self.memory_data:
            data_array = np.array(list(self.memory_data))
            if len(data_array) > 3:
                # Smoother line
                self.ax2.plot(
                    time_indices, 
                    data_array, 
                    color=memory_color, 
                    linewidth=3, 
                    marker='o', 
                    markersize=4,
                    alpha=0.9,
                    markerfacecolor='white',
                    markeredgecolor=memory_color,
                    markeredgewidth=1,
                    zorder=5
                )
                # Gradient fill below the line
                self.ax2.fill_between(
                    time_indices, 
                    data_array,
                    alpha=0.25,
                    color=memory_color,
                    linewidth=0,
                    zorder=4
                )
                
                # Add shadow effect to line
                self.ax2.plot(
                    time_indices, 
                    data_array, 
                    color='#000000', 
                    linewidth=4,
                    alpha=0.05,
                    zorder=3
                )
                
        memory_ymax = max(100, max(self.memory_data) * 1.1 if self.memory_data else 100)
        self.ax2.set_ylim(0, memory_ymax)
        self.ax2.set_title("Memory Usage (%)", fontsize=11, fontweight='bold', color="#333333")
        
        # Plot Network usage with sexy styling
        upload_color = '#107c10'  # Green
        download_color = '#ff8c00'  # Orange
        
        # Use different markers for visual distinction
        if self.network_sent_data and self.network_recv_data:
            sent_array = np.array(list(self.network_sent_data))
            recv_array = np.array(list(self.network_recv_data))
            
            # Plot upload with light shadow
            if len(sent_array) > 1:
                self.ax3.plot(
                    time_indices, 
                    sent_array,
                    color=upload_color, 
                    linewidth=3, 
                    marker='o', 
                    markersize=4,
                    alpha=0.9,
                    markerfacecolor='white',
                    markeredgecolor=upload_color,
                    markeredgewidth=1,
                    zorder=6,
                    label='Upload'
                )
                # Add shadow
                self.ax3.plot(
                    time_indices, 
                    sent_array, 
                    color='#000000', 
                    linewidth=4,
                    alpha=0.05,
                    zorder=3
                )
                
            # Plot download with light shadow
            if len(recv_array) > 1:
                self.ax3.plot(
                    time_indices, 
                    recv_array, 
                    color=download_color, 
                    linewidth=3, 
                    marker='s',  # Square marker for distinction
                    markersize=4,
                    alpha=0.9,
                    markerfacecolor='white',
                    markeredgecolor=download_color,
                    markeredgewidth=1,
                    zorder=5,
                    label='Download'
                )
                # Add shadow
                self.ax3.plot(
                    time_indices, 
                    recv_array, 
                    color='#000000', 
                    linewidth=4,
                    alpha=0.05,
                    zorder=2
                )
                
            # Add subtle area fill for both
            if len(sent_array) > 1:
                self.ax3.fill_between(
                    time_indices, 
                    sent_array,
                    alpha=0.15,
                    color=upload_color,
                    zorder=4
                )
                
            if len(recv_array) > 1:
                self.ax3.fill_between(
                    time_indices, 
                    recv_array,
                    alpha=0.10,
                    color=download_color,
                    zorder=3
                )
        
        network_ymax = max(0.1, max([max(self.network_sent_data, default=0.1), 
                                   max(self.network_recv_data, default=0.1)]) * 1.2)
        self.ax3.set_ylim(0, network_ymax)
        
        # Create a cool legend with custom styling
        legend = self.ax3.legend(
            loc='upper right', 
            frameon=True,
            facecolor='#f8f8f8',
            framealpha=0.9,
            edgecolor='#dddddd',
            fontsize=9
        )
        
        self.ax3.set_title("Network Usage (MB/s)", fontsize=11, fontweight='bold', color="#333333")
        
        # Handle x-axis ticks for all graphs - use actual timestamps but fewer of them
        for ax in [self.ax1, self.ax2, self.ax3]:
            # Only show a reasonable number of timestamps on the x-axis
            num_to_show = min(5, len(self.time_data))
            if num_to_show > 1 and len(self.time_data) > 0:
                # Show timestamps at regular intervals
                indices = np.linspace(0, len(self.time_data)-1, num_to_show, dtype=int)
                ax.set_xticks(indices)
                ax.set_xticklabels([list(self.time_data)[i] for i in indices], rotation=45)
        
        # Adjust layout and draw with extra padding
        self.fig.tight_layout()
        self.canvas.draw()
        
        # Schedule next update
        self.root.after(2000, self.update_stats)
    
    def analyze_processes_with_gemini(self):
        if self.gemini_analyzing:
            messagebox.showinfo("Info", "Process analysis is already running")
            return
            
        self.gemini_analyzing = True
        
        def analysis_task():
            try:
                # Get detailed process information
                process_info = []
                for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time', 'status']):
                    try:
                        pinfo = proc.info
                        # Add more details about the process
                        if pinfo['cpu_percent'] > 0.1 or pinfo['memory_percent'] > 0.1:  # Filter out minimal usage processes
                            try:
                                proc_obj = psutil.Process(pinfo['pid'])
                                pinfo['cmdline'] = ' '.join(proc_obj.cmdline())
                            except:
                                pinfo['cmdline'] = "Unknown"
                            process_info.append(pinfo)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
                
                # Sort by resource usage (CPU + Memory)
                process_info.sort(key=lambda x: (x['cpu_percent'] + x['memory_percent']), reverse=True)
                top_processes = process_info[:20]  # Focus on top resource consumers
                
                # Format process data for Gemini
                process_text = "Here are my current running processes:\n\n"
                for idx, proc in enumerate(top_processes):
                    process_text += f"{idx+1}. Name: {proc['name']}\n"
                    process_text += f"   PID: {proc['pid']}\n"
                    process_text += f"   CPU: {proc['cpu_percent']:.2f}%\n"
                    process_text += f"   Memory: {proc['memory_percent']:.2f}%\n"
                    process_text += f"   Command: {proc.get('cmdline', 'Unknown')}\n"
                    process_text += f"   Status: {proc['status']}\n\n"
                
                prompt = f"""
                {process_text}
                
                Based on this list of processes running on my Windows system, please:
                1. Identify which processes are safe to close and which are critical system processes
                2. Explain what each process does in simple terms
                3. Recommend which processes I could close to improve performance
                4. Identify any suspicious or resource-intensive processes that might need attention
                
                Format your response in clear sections with bullet points where appropriate.
                """
                
                # Call Gemini API
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=prompt
                )
                
                # Update the UI with results
                self.gemini_result = response.text
                self.update_gemini_results()
                
            except Exception as e:
                self.gemini_result = f"Error analyzing processes: {str(e)}"
                self.update_gemini_results()
            
            finally:
                self.gemini_analyzing = False
        
        # Start analysis in a separate thread to keep UI responsive
        threading.Thread(target=analysis_task, daemon=True).start()
        
        # Show loading message
        self.gemini_result = "Analyzing processes with Gemini AI... Please wait."
        self.update_gemini_results()
    
    def update_gemini_results(self):
        # Update the results text widget on the main thread
        if hasattr(self, 'gemini_results_text'):
            self.gemini_results_text.config(state="normal")
            self.gemini_results_text.delete(1.0, tk.END)
            self.gemini_results_text.insert(tk.END, self.gemini_result if self.gemini_result else "No analysis available yet.")
            self.gemini_results_text.config(state="disabled")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SystemMonitor()
    app.run()
