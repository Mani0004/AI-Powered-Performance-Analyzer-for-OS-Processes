import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import os
from dotenv import load_dotenv
import openai
from datetime import datetime

class SystemMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI-Powered OS Performance Analyzer")
        self.root.geometry("800x600")
        
        # Load OpenAI API key from .env file
        load_dotenv()
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        self.setup_ui()
        self.update_stats()
    
    def setup_ui(self):
        # System Stats Frame
        stats_frame = ttk.LabelFrame(self.root, text="System Statistics", padding=10)
        stats_frame.pack(fill="x", padx=10, pady=5)
        
        # CPU Usage
        self.cpu_label = ttk.Label(stats_frame, text="CPU Usage: ")
        self.cpu_label.pack()
        
        # Memory Usage
        self.memory_label = ttk.Label(stats_frame, text="Memory Usage: ")
        self.memory_label.pack()
        
        # Disk Usage
        self.disk_label = ttk.Label(stats_frame, text="Disk Usage: ")
        self.disk_label.pack()
        
        # Process List Frame
        process_frame = ttk.LabelFrame(self.root, text="Top 5 Processes", padding=10)
        process_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Process Treeview
        self.process_tree = ttk.Treeview(process_frame, columns=("Name", "PID", "CPU%", "Memory%"), show="headings")
        self.process_tree.heading("Name", text="Name")
        self.process_tree.heading("PID", text="PID")
        self.process_tree.heading("CPU%", text="CPU%")
        self.process_tree.heading("Memory%", text="Memory%")
        self.process_tree.pack(fill="both", expand=True)
        
        # AI Suggestions Frame
        ai_frame = ttk.LabelFrame(self.root, text="AI Suggestions", padding=10)
        ai_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # AI Suggestions Text
        self.suggestions_text = tk.Text(ai_frame, height=6, wrap=tk.WORD)
        self.suggestions_text.pack(fill="both", expand=True)
        
        # Get AI Suggestions Button
        self.suggest_button = ttk.Button(ai_frame, text="Get AI Suggestions", command=self.get_ai_suggestions)
        self.suggest_button.pack(pady=5)
    
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
        top_processes = processes[:5]
        
        # Clear existing items
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)
        
        # Add new items
        for proc in top_processes:
            self.process_tree.insert("", "end", values=(
                proc['name'],
                proc['pid'],
                f"{proc['cpu_percent']:.1f}",
                f"{proc['memory_percent']:.1f}"
            ))
        
        # Schedule next update and get AI suggestions
        self.get_ai_suggestions()
        self.root.after(2000, self.update_stats)
    
    def get_ai_suggestions(self, show_error=True):
        try:
            # Collect current system stats
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Prepare system status message
            status_msg = f"System Status:\n"
            status_msg += f"CPU Usage: {cpu_percent}%\n"
            status_msg += f"Memory Usage: {memory.percent}%\n"
            status_msg += f"Disk Usage: {disk.percent}%\n\n"
            status_msg += "Top Processes:\n"
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent'])[:5]:
                try:
                    pinfo = proc.info
                    status_msg += f"{pinfo['name']}: CPU {pinfo['cpu_percent']:.1f}%, Memory {pinfo['memory_percent']:.1f}%\n"
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Get AI suggestions
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a system performance analyst. Provide concise, practical suggestions for optimizing system performance based on the current status."},
                    {"role": "user", "content": f"Given this system status, suggest performance optimization steps:\n{status_msg}"}
                ]
            )
            
            # Display suggestions
            suggestions = response['choices'][0]['message']['content']
            self.suggestions_text.delete(1.0, tk.END)
            self.suggestions_text.insert(tk.END, suggestions)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get AI suggestions: {str(e)}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SystemMonitor()
    app.run()