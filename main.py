import tkinter as tk
from tkinter import messagebox

from taplite.single_instance import SingleInstance, activate_existing_window
from taplite.ui import main


if __name__ == "__main__":
    instance = SingleInstance("Local\\TapLite.SingleInstance")
    if not instance.acquire():
        if not activate_existing_window("TapLite"):
            dialog = tk.Tk()
            dialog.withdraw()
            messagebox.showinfo("TapLite", "TapLite 已在运行。")
            dialog.destroy()
        raise SystemExit(0)

    try:
        main()
    finally:
        instance.release()
