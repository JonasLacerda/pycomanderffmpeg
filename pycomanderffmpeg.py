import tkinter as tk
from tkinter import ttk
import subprocess
import time
import os
import atexit
from threading import Thread
import signal

class CommandManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Command Manager")

        self.command_entry = tk.Entry(root, width=50)
        self.command_entry.pack(pady=10)
        self.command_entry.bind('<Button-1>', self.paste_from_clipboard)

        self.run_button = tk.Button(root, text="Run Command", command=self.run_command)
        self.run_button.pack(pady=5)

        # Create a treeview with columns
        self.tree = ttk.Treeview(root, columns=("Command", "Time"), show="headings")
        self.tree.heading("Command", text="Command")
        self.tree.heading("Time", text="Time")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.processes = {}

        # Start a thread to monitor the processes
        self.monitor_thread = Thread(target=self.monitor_processes, daemon=True)
        self.monitor_thread.start()

        # Register the exit function
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)  # Handle window close event
        atexit.register(self.terminate_all_processes)

    def paste_from_clipboard(self, event):
        clipboard_content = self.root.clipboard_get()  # Get the content of the clipboard
        self.command_entry.delete(0, tk.END)  # Clear the existing content
        self.command_entry.insert(0, clipboard_content)  # Insert the clipboard content

    def extract_filename(self, command):
        # Extract the filename from the command
        parts = command.split()
        for i, part in enumerate(parts):
            if part.endswith('.mp4') or part.endswith('.mkv') or part.endswith('.avi'):
                return os.path.basename(part)
        return 'Unknown file'

    def run_command(self):
        command = self.command_entry.get()
        if command:
            start_time = time.time()
            # Do not capture stdout and stderr to avoid buffer issues
            proc = subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
            self.processes[proc] = {'command': command, 'start_time': start_time}
            self.update_command_list()
            self.command_entry.delete(0, tk.END)  # Clear the input field

    def update_command_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for proc, info in self.processes.items():
            elapsed_time = time.time() - info['start_time']
            
            # Calcular minutos e horas
            hours = int(elapsed_time // 3600)
            minutes = int((elapsed_time % 3600) // 60)
            seconds = int(elapsed_time % 60)

            if hours > 0:
                elapsed_time_str = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                elapsed_time_str = f"{minutes}m {seconds}s"
            else:
                elapsed_time_str = f"{seconds}s"

            # Extract filename
            filename = self.extract_filename(info['command'])
            display_command = filename if filename != 'Unknown file' else info['command'][:20] + '...' if len(info['command']) > 20 else info['command']
            
            # Add command and elapsed time to the treeview
            self.tree.insert("", "end", values=(display_command, elapsed_time_str))
            self.tree.bind("<ButtonRelease-1>", self.on_treeview_click)

    def on_treeview_click(self, event):
        item = self.tree.selection()
        if item:
            selected_item = item[0]
            command = self.tree.item(selected_item, 'values')[0]
            for proc in self.processes:
                if command in self.processes[proc]['command']:
                    self.stop_command(proc)
                    break

    def stop_command(self, proc):
        try:
            # Send SIGTERM to the process group to terminate it
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)  # Wait for the process to terminate
        except subprocess.TimeoutExpired:
            # If the process does not terminate, force kill it
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        finally:
            # Remove the process from the list and update the UI
            self.processes.pop(proc, None)
            self.update_command_list()

    def terminate_all_processes(self):
        for proc in list(self.processes.keys()):
            self.stop_command(proc)
        self.processes.clear()

    def monitor_processes(self):
        while True:
            # Poll each process to check if it has terminated
            to_remove = [proc for proc in self.processes if proc.poll() is not None]
            if to_remove:
                for proc in to_remove:
                    self.processes.pop(proc, None)
            self.update_command_list()
            time.sleep(1)

    def on_close(self):
        self.terminate_all_processes()  # Ensure all processes are terminated
        self.root.destroy()  # Close the window

if __name__ == "__main__":
    root = tk.Tk()
    app = CommandManager(root)
    root.mainloop()
