import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
import numpy as np
from collections import deque

# ---------------- GLOBALS ----------------
process_list = []
root = tk.Tk()
algo_var = tk.StringVar(value="FCFS")

arrival_entry = None
burst_entry = None
quantum_entry = None
process_display = None
quantum_frame = None
report_label = None # Summary report ke liye

# ---------------- DVFS LOGIC (Theoretical Simulation) ----------------
def calculate_dvfs_power(burst_time):
    # Agar burst time 10 se zyada hai toh High Frequency (Turbo Mode)
    # Agar kam hai toh Low Frequency (Power Save Mode)
    if burst_time > 10:
        return "High (Turbo)", "2.4W"
    else:
        return "Low (Eco)", "0.8W"

# ---------------- SCHEDULING ALGORITHMS ----------------
def energy_efficient_fcfs(processes):
    processes.sort(key=lambda x: x['arrival'])
    time = 0
    completed = []
    for p in processes:
        if time < p['arrival']: time = p['arrival']
        p['start_time'] = time
        p['dvfs_mode'], p['power'] = calculate_dvfs_power(p['burst'])
        p['completion'] = time + p['burst']
        p['turnaround'] = p['completion'] - p['arrival']
        p['waiting'] = p['turnaround'] - p['burst']
        time = p['completion']
        completed.append(p)
    return completed

def energy_efficient_sjf(processes):
    time = 0
    completed = []
    procs = [p.copy() for p in processes]
    while procs:
        available = [p for p in procs if p['arrival'] <= time]
        if not available:
            time = min(p['arrival'] for p in procs)
            continue
        current = min(available, key=lambda x: x['burst'])
        procs.remove(current)
        current['start_time'] = time
        current['dvfs_mode'], current['power'] = calculate_dvfs_power(current['burst'])
        current['completion'] = time + current['burst']
        current['turnaround'] = current['completion'] - current['arrival']
        current['waiting'] = current['turnaround'] - current['burst']
        time = current['completion']
        completed.append(current)
    return completed

def energy_efficient_round_robin(processes, quantum):
    time = 0
    completed = []
    ready_queue = sorted([p.copy() for p in processes], key=lambda x: x['arrival'])
    for p in ready_queue: p['remaining'] = p['burst']
    
    queue = deque()
    current_idx = 0
    while queue or current_idx < len(ready_queue):
        if not queue and current_idx < len(ready_queue):
            time = max(time, ready_queue[current_idx]['arrival'])
            while current_idx < len(ready_queue) and ready_queue[current_idx]['arrival'] <= time:
                queue.append(ready_queue[current_idx])
                current_idx += 1
        
        p = queue.popleft()
        if 'start_time' not in p: p['start_time'] = time
        p['dvfs_mode'], p['power'] = calculate_dvfs_power(p['burst']) # Simplified for RR
        
        execution_time = min(p['remaining'], quantum)
        time += execution_time
        p['remaining'] -= execution_time
        
        while current_idx < len(ready_queue) and ready_queue[current_idx]['arrival'] <= time:
            queue.append(ready_queue[current_idx])
            current_idx += 1
            
        if p['remaining'] > 0:
            queue.append(p)
        else:
            p['completion'] = time
            p['turnaround'] = p['completion'] - p['arrival']
            p['waiting'] = p['turnaround'] - p['burst']
            completed.append(p)
    return completed

# ---------------- GUI FUNCTIONS ----------------
def add_process():
    try:
        arrival = int(arrival_entry.get())
        burst = int(burst_entry.get())
        if arrival < 0 or burst <= 0: raise ValueError
        pid = len(process_list) + 1
        process_list.append({'id': pid, 'arrival': arrival, 'burst': burst})
        process_display.insert("", "end", values=(pid, arrival, burst))
        arrival_entry.delete(0, tk.END)
        burst_entry.delete(0, tk.END)
    except ValueError:
        messagebox.showerror("Error", "Enter valid Arrival & Burst Time!")

def remove_process():
    selected_item = process_display.selection()
    if not selected_item:
        messagebox.showwarning("Selection Error", "Please select a process!")
        return
    for item in selected_item:
        values = process_display.item(item, "values")
        global process_list
        process_list = [p for p in process_list if p['id'] != int(values[0])]
        process_display.delete(item)

def update_report(results):
    avg_wait = sum(p['waiting'] for p in results) / len(results)
    avg_tat = sum(p['turnaround'] for p in results) / len(results)
    eco_count = sum(1 for p in results if p['dvfs_mode'] == "Low (Eco)")
    
    report_text = f"Average Waiting Time: {avg_wait:.2f}ms  |  " \
                  f"Average Turnaround: {avg_tat:.2f}ms  |  " \
                  f"DVFS Eco Mode Active: {eco_count} Processes"
    report_label.config(text=report_text)

def run_scheduling():
    if not process_list:
        messagebox.showerror("Error", "No processes added!")
        return
    algo = algo_var.get()
    if algo == "FCFS": result = energy_efficient_fcfs(process_list)
    elif algo == "SJF": result = energy_efficient_sjf(process_list)
    else:
        try:
            q = int(quantum_entry.get())
            result = energy_efficient_round_robin(process_list, q)
        except: return
    
    update_report(result)
    show_gantt(result)

def show_gantt(results):
    fig, ax = plt.subplots(figsize=(10, 4))
    # DVFS Visualization: Color based on Power Mode
    for i, p in enumerate(results):
        start = p.get('start_time', p['completion'] - p['burst'])
        duration = p['completion'] - start
        color = "#22C55E" if p['dvfs_mode'] == "Low (Eco)" else "#EF4444"
        ax.broken_barh([(start, duration)], (10, 9), facecolors=color)
        ax.text(start + duration/2, 14.5, f"P{p['id']}\n{p['power']}", ha='center', va='center', color="white", fontsize=9, fontweight='bold')
    
    ax.set_xlabel("Time (ms)")
    ax.set_yticks([])
    ax.set_title(f"Energy-Aware Gantt Chart (Red: High Power, Green: Eco Mode)")
    plt.tight_layout()
    plt.show()

def toggle_quantum(*_):
    if algo_var.get() == "Round Robin": quantum_frame.pack(fill="x", pady=8)
    else: quantum_frame.pack_forget()

# ---------------- GUI SETUP ----------------
def setup_gui():
    global arrival_entry, burst_entry, quantum_entry, process_display, quantum_frame, report_label

    root.title("⚡ DVFS Energy-Efficient CPU Scheduler")
    root.geometry("1100x650")
    root.configure(bg="#0F172A")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#1E293B", foreground="white", fieldbackground="#1E293B", rowheight=35, font=("Segoe UI", 11))
    style.configure("Treeview.Heading", background="#334155", foreground="white", font=("Segoe UI", 12, "bold"))
    style.map("Treeview", background=[('selected', '#38BDF8')])

    main = tk.Frame(root, bg="#0F172A")
    main.pack(fill="both", expand=True, padx=20, pady=10)

    # LEFT PANEL
    left = tk.Frame(main, bg="#111827", padx=15, pady=15)
    left.pack(side="left", fill="y", padx=(0, 15))

    tk.Label(left, text="Configuration", fg="#38BDF8", bg="#111827", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 10))
    
    tk.Label(left, text="Algorithm", fg="white", bg="#111827").pack(anchor="w")
    algo_box = ttk.Combobox(left, textvariable=algo_var, values=["FCFS", "SJF", "Round Robin"], state="readonly", font=("Segoe UI", 11))
    algo_box.pack(fill="x", pady=(0, 10))
    algo_box.bind("<<ComboboxSelected>>", toggle_quantum)

    tk.Label(left, text="Arrival Time", fg="white", bg="#111827").pack(anchor="w")
    arrival_entry = ttk.Entry(left, font=("Segoe UI", 11))
    arrival_entry.pack(fill="x", pady=(0, 10))

    tk.Label(left, text="Burst Time", fg="white", bg="#111827").pack(anchor="w")
    burst_entry = ttk.Entry(left, font=("Segoe UI", 11))
    burst_entry.pack(fill="x", pady=(0, 10))

    quantum_frame = tk.Frame(left, bg="#111827")
    tk.Label(quantum_frame, text="Time Quantum", fg="white", bg="#111827").pack(anchor="w")
    quantum_entry = ttk.Entry(quantum_frame, font=("Segoe UI", 11))
    quantum_entry.insert(0, "4")
    quantum_entry.pack(fill="x")

    ttk.Button(left, text="➕ Add Process", command=add_process).pack(fill="x", pady=(20, 5))
    ttk.Button(left, text="▶ Run Simulation", command=run_scheduling).pack(fill="x", pady=10)

    # RIGHT PANEL
    right = tk.Frame(main, bg="#0F172A")
    right.pack(side="right", fill="both", expand=True)

    header = tk.Frame(right, bg="#0F172A")
    header.pack(fill="x")
    tk.Label(header, text="Energy-Efficient ⚡ CPU Scheduler ", fg="white", bg="#0F172A", font=("Segoe UI", 16, "bold")).pack(side="left")
    tk.Button(header, text="🗑 Remove Selected", command=remove_process, bg="#EF4444", fg="white", font=("Segoe UI", 9, "bold"), border=0, padx=10, cursor="hand2").pack(side="right")

    process_display = ttk.Treeview(right, columns=("PID", "Arrival", "Burst"), show="headings", style="Treeview")
    for col in ("PID", "Arrival", "Burst"):
        process_display.heading(col, text=col, anchor="center")
        process_display.column(col, anchor="center")
    process_display.pack(fill="both", expand=True, pady=10)

    # --- EFFICIENCY REPORT BOX ---
    report_frame = tk.LabelFrame(right, text=" ⚡ Efficiency & DVFS Report ", fg="#38BDF8", bg="#1E293B", font=("Segoe UI", 10, "bold"), padx=10, pady=10)
    report_frame.pack(fill="x", pady=(10, 0))
    report_label = tk.Label(report_frame, text="Run simulation to see efficiency metrics...", fg="white", bg="#1E293B", font=("Segoe UI", 11))
    report_label.pack(anchor="w")

    toggle_quantum()

if __name__ == "__main__":
    setup_gui()
    root.mainloop()