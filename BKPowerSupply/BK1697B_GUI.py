import serial
import time
import threading
import csv
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from collections import deque

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from  BK1697B import BK1697B

# -------------------------
# Tkinter GUI
# -------------------------
class BK1697B_GUI:
    def __init__(self, master):
        self.master = master
        master.title("BK1697B Power Supply Controller")
        master.geometry("900x700")

        # Device + monitor control
        self.device: Optional[BK1697B] = None
        self.monitoring = False
        ts = datetime.now()
        formatted_date = ts.strftime("%Y-%m-%d-%H-%M-%S")
        self.csv_file = f"bk1697b_log_{formatted_date}.csv"
        self.status_summary = "Disconnected;NOTSet-VoltageCurrent;DisableOutput;Stop-Monitoring"

        # Thresholds
        self.volt_thresh = 14.0
        self.curr_thresh = 2.5

        # Data buffers (last 30 min)
        self.time_window = timedelta(minutes=30)
        self.data_lock = threading.Lock()
        self.times = deque()
        self.volts = deque()
        self.currs = deque()

        # --- GUI Layout ---
        frm = ttk.Frame(master, padding=10)
        frm.pack(side=tk.TOP, fill=tk.X)

        # Styles for ttk buttons (ttk widgets don't accept the `background` option directly)
        self.style = ttk.Style()
        try:
            # 'clam' theme usually respects background color settings
            self.style.theme_use('clam')
        except Exception:
            pass
        # Define styles for connected/disconnected and enable/disable states
        self.style.configure('Connected.TButton', background='yellow')
        self.style.configure('Enable.TButton', background='green')
        self.style.configure('Disable.TButton', background='red')

        #row - 0
        ttk.Label(frm, text="Port:").grid(column=0, row=0, sticky="e")
        self.port_entry = ttk.Entry(frm)
        self.port_entry.insert(0, "/dev/ttyACM0")
        self.port_entry.grid(column=1, row=0)

        self.connect_btn = ttk.Button(frm, text="Connect", command=self.connect_device)
        self.connect_btn.grid(column=2, row=0, padx=5)

        #row - 1,2
        ttk.Label(frm, text="Set Voltage (V):").grid(column=0, row=1, sticky="e")
        self.volt_entry = ttk.Entry(frm)
        self.volt_entry.insert(0, "9.00")
        self.volt_entry.grid(column=1, row=1)

        ttk.Label(frm, text="Set Current Limit (A):").grid(column=0, row=2, sticky="e")
        self.curr_entry = ttk.Entry(frm)
        self.curr_entry.insert(0, "2.50")
        self.curr_entry.grid(column=1, row=2)

        # row 1,2
        self.set_btn = ttk.Button(frm, text="Apply Settings", command=self.apply_settings)
        self.set_btn.grid(column=2, row=1, rowspan=2, padx=5)

        # row 3,4
        ttk.Label(frm, text="Voltage Threshold (V):").grid(column=0, row=3, sticky="e")
        self.volt_thresh_entry = ttk.Entry(frm)
        self.volt_thresh_entry.insert(0, str(self.volt_thresh))
        self.volt_thresh_entry.grid(column=1, row=3)

        ttk.Label(frm, text="Current Threshold (A):").grid(column=0, row=4, sticky="e")
        self.curr_thresh_entry = ttk.Entry(frm)
        self.curr_thresh_entry.insert(0, str(self.curr_thresh))
        self.curr_thresh_entry.grid(column=1, row=4)

        # row 5
        self.enable_btn = ttk.Button(frm, text="Enable Output", command=self.toggle_output)
        self.enable_btn.grid(column=1, row=5, rowspan=1, padx=5)

        # row 6,7,8
        self.start_btn = ttk.Button(frm, text="Start I-V Monitoring", command=self.start_monitoring)
        self.start_btn.grid(column=0, row=6, pady=10)

        self.stop_btn = ttk.Button(frm, text="Stop I-V Monitoring", command=self.stop_monitoring)
        self.stop_btn.grid(column=1, row=6, pady=10)

        # Button to read current measured voltage and current immediately
        self.read_btn = ttk.Button(frm, text="Read Measurements Once", command=self.get_measurements)
        self.read_btn.grid(column=2, row=6, pady=10, columnspan=2)

        # Live readings
        ttk.Label(frm, text="Voltage:").grid(column=0, row=7, sticky="e")
        self.volt_value = ttk.Label(frm, text="--", font=("Helvetica", 14))
        self.volt_value.grid(column=1, row=7)

        ttk.Label(frm, text="Current:").grid(column=0, row=8, sticky="e")
        self.curr_value = ttk.Label(frm, text="--", font=("Helvetica", 14))
        self.curr_value.grid(column=1, row=8)

        # Matplotlib plot
        self.fig, self.ax = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
        self.fig.subplots_adjust(hspace=0.3)
        self.ax[0].set_ylabel("Voltage (V)")
        self.ax[1].set_ylabel("Current (A)")
        self.ax[1].set_xlabel("Time")
        self.volt_line, = self.ax[0].plot([], [], 'b-o', markersize=3)
        self.curr_line, = self.ax[1].plot([], [], 'r-o', markersize=3)
        self.canvas = FigureCanvasTkAgg(self.fig, master)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Start periodic plot update
        self.update_plot()

        self.quit_btn = ttk.Button(frm, text="Quit", command=self.shutdown, style='Disable.TButton')
        self.quit_btn.grid(column=2, row=10, pady=10, sticky="e")

        self.status_label = ttk.Label(frm, text="Instant Status: Disconnected")
        self.status_label.grid(column=2, row=9, columnspan=1)

        # Ensure graceful shutdown when window is closed via the window manager
        try:
            master.protocol("WM_DELETE_WINDOW", self.shutdown)
        except Exception:
            pass

    # -------------------------
    # GUI Functions
    # -------------------------
    def connect_device(self):
        port = self.port_entry.get().strip()
        try:
            # If already connected, disconnect/close the device
            if self.device:
                # stop monitoring if running
                if self.monitoring:
                    self.monitoring = False
                    self.status_label.config(text="Monitoring stopped due to disconnect.")
                try:
                    self.device.close()
                except Exception as e:
                    print("Error closing device:", e)
                self.device = None
                self.connect_btn.config(text="Connect")
                self.status_label.config(text="Instant Status: Disconnected")
                return

            # Otherwise, create a new device instance (constructor opens serial port)
            self.device = BK1697B(port)
            # Use a ttk style instead of background option
            self.connect_btn.config(text="Disconnect", style='Connected.TButton')
            self.status_label.config(text=f"Connected to port {port}")

            # Check if output is enabled and update the enable button accordingly
            if self.device.get_output_state():
                self.enable_btn.config(text="Disable Output", style='Enable.TButton')
            else:
                self.enable_btn.config(text="Enable Output", style='Disable.TButton')

        except Exception as e:
            messagebox.showerror("Connection Error", str(e))

    def shutdown(self):
        """Gracefully stop monitoring, close device if connected, and destroy GUI."""
        # Stop monitoring loop
        if self.monitoring:
            self.monitoring = False
            # small pause to allow background thread to exit
            time.sleep(0.2)

        # Close device serial port if connected
        if self.device:
            try:
                self.device.close()
            except Exception as e:
                print("Error during device.close():", e)
            self.device = None

        # Destroy the Tk window
        try:
            self.master.destroy()
        except Exception as e:
            print("Error destroying master:", e)

    def get_measurements(self):
        """Read measured voltage and current from the device and update labels."""
        if not self.device:
            messagebox.showwarning("Warning", "Device not connected.")
            return
        try:
            raw_v = self.device.measure_voltage()
            raw_c = self.device.measure_current()

            v = None
            c = None
            # Try to convert to float if possible
            try:
                v = float(raw_v)
            except Exception:
                v = None
            try:
                c = float(raw_c)
            except Exception:
                c = None

            # Update GUI labels with formatted numeric values when possible
            if v is not None:
                self.volt_value.config(text=f"{v:.3f} V",
                                       foreground="red" if v and v > self.volt_thresh else "black")
            else:
                self.volt_value.config(text=f"{raw_v}" if raw_v else "--")

            if c is not None:
                self.curr_value.config(text=f"{c:.3f} A",
                                       foreground="red" if c and c > self.curr_thresh else "black")
            else:
                self.curr_value.config(text=f"{raw_c}" if raw_c else "--")

            self.status_label.config(text="Instant Status: Measurements updated.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read measurements: {e}")

    def apply_settings(self):
        if not self.device:
            messagebox.showwarning("Warning", "Device not connected.")
            return
        try:
            v = float(self.volt_entry.get())
            c = float(self.curr_entry.get())
            self.volt_thresh = float(self.volt_thresh_entry.get())
            self.curr_thresh = float(self.curr_thresh_entry.get())
            self.device.set_voltage(v)
            self.device.set_current(c)
            self.device.set_upperlimit_voltage(self.volt_thresh)
            self.device.set_upperlimit_current(self.curr_thresh)
            self.status_label.config(text=f"Instant Status: Set {v:.2f} V, {c:.3f} A")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def toggle_output(self):
        if not self.device:
            messagebox.showwarning("Warning", "Device not connected.")
            return
        try:
            state = self.device.get_output_state()
            if state:
                self.device.turnoff_output()
                self.enable_btn.config(text="Enable Output")
                self.status_label.config(text="Instant Status: Output Disabled")
            else:
                self.device.turnon_output()
                self.enable_btn.config(text="Disable Output")
                self.status_label.config(text="Instant Status: Output Enabled")
        except Exception as e:
            messagebox.showerror("Error", str(e))   
    
    def start_monitoring(self):
        if not self.device:
            messagebox.showwarning("Warning", "Connect to device first.")
            return
        if self.monitoring:
            return
        self.monitoring = True
        self.status_label.config(text="Instant Status: Monitoring started.")
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def stop_monitoring(self):
        self.monitoring = False
        self.status_label.config(text="Instant Status: Monitoring stopped.")

    def _monitor_loop(self):
        with open(self.csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "voltage", "current"])
            while self.monitoring:
                try:
                    v = self.device.measure_voltage()
                    c = self.device.measure_current()
                    ts = datetime.now()

                    with self.data_lock:
                        self.times.append(ts)
                        self.volts.append(v)
                        self.currs.append(c)
                        # Keep only last 30 min
                        while self.times and ts - self.times[0] > self.time_window:
                            self.times.popleft()
                            self.volts.popleft()
                            self.currs.popleft()

                    self.volt_value.config(text=f"{v:.3f} V" if v else "--",
                                           foreground="red" if v and v > self.volt_thresh else "black")
                    self.curr_value.config(text=f"{c:.3f} A" if c else "--",
                                           foreground="red" if c and c > self.curr_thresh else "black")

                    # Alerts
                    if v and v > self.volt_thresh:
                        self._alert(f"Voltage exceeds {self.volt_thresh} V!")
                    if c and c > self.curr_thresh:
                        self._alert(f"Current exceeds {self.curr_thresh} A!")

                    writer.writerow([ts.strftime("%Y-%m-%d %H:%M:%S"), v, c])
                    f.flush()
                except Exception as e:
                    print("Monitor error:", e)
                time.sleep(10)  # read every 10 s

    def _alert(self, msg: str):
        self.master.after(0, lambda: messagebox.showwarning("Threshold Alert", msg))

    def update_plot(self):
        """Refresh live plot every minute."""
        if self.times:
            with self.data_lock:
                t = list(self.times)
                v = list(self.volts)
                c = list(self.currs)
            self.volt_line.set_data(t, v)
            self.curr_line.set_data(t, c)
            self.ax[0].relim()
            self.ax[0].autoscale_view()
            self.ax[1].relim()
            self.ax[1].autoscale_view()
            self.fig.autofmt_xdate()
            self.canvas.draw()
        self.master.after(60000, self.update_plot)  # update every minute


# -------------------------
# Run GUI
# -------------------------
if __name__ == "__main__":
    root = tk.Tk()
    gui = BK1697B_GUI(root)
    root.mainloop()
