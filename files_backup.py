#!/usr/bin/env python3
"""
Folder Cleanup and SCP Transfer Tool

This script:
1. Scans selected folders and removes empty directories (including nested empty dirs)
2. Uses SCP to transfer cleaned folders to a remote target location
3. Provides a tkinter GUI for folder selection and configuration
"""

import os
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading
from typing import List, Set


class FolderCleanupSCP:
    def __init__(self, root):
        self.root = root
        self.root.title("Folder Cleanup & SCP Transfer Tool")
        self.root.geometry("800x600")
        
        self.selected_folders = []
        self.removed_folders = []
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Folder selection section
        ttk.Label(main_frame, text="Source Folders:", font=('Arial', 12, 'bold')).grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10)
        )
        
        ttk.Button(main_frame, text="Add Folder", command=self.add_folder).grid(
            row=1, column=0, sticky=tk.W, padx=(0, 10)
        )
        
        ttk.Button(main_frame, text="Remove Selected", command=self.remove_selected_folder).grid(
            row=1, column=1, sticky=tk.W, padx=(0, 10)
        )
        
        ttk.Button(main_frame, text="Clear All", command=self.clear_all_folders).grid(
            row=1, column=2, sticky=tk.W
        )
        
        # Folder listbox with scrollbar
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 20))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        self.folder_listbox = tk.Listbox(list_frame, height=8)
        self.folder_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.folder_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.folder_listbox.configure(yscrollcommand=scrollbar.set)
        
        # SCP configuration section
        ttk.Label(main_frame, text="SCP Configuration:", font=('Arial', 12, 'bold')).grid(
            row=3, column=0, columnspan=3, sticky=tk.W, pady=(20, 10)
        )
        
        # Remote host
        ttk.Label(main_frame, text="Remote Host:").grid(row=4, column=0, sticky=tk.W)
        self.host_entry = ttk.Entry(main_frame, width=30)
        self.host_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        self.host_entry.insert(0, "user@hostname")
        
        # Remote path
        ttk.Label(main_frame, text="Remote Path:").grid(row=5, column=0, sticky=tk.W, pady=(10, 0))
        self.path_entry = ttk.Entry(main_frame, width=30)
        self.path_entry.grid(row=5, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=(10, 0))
        self.path_entry.insert(0, "/remote/target/path/")
        
        # Options
        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="Recursive SCP (-r)", variable=self.recursive_var).grid(
            row=6, column=0, columnspan=2, sticky=tk.W, pady=(10, 0)
        )
        
        self.preserve_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="Preserve attributes (-p)", variable=self.preserve_var).grid(
            row=7, column=0, columnspan=2, sticky=tk.W, pady=(5, 0)
        )
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=8, column=0, columnspan=3, pady=(20, 0))
        
        ttk.Button(button_frame, text="1. Clean Folders Only", 
                  command=self.clean_folders_only).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="2. Clean & Transfer", 
                  command=self.clean_and_transfer).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="3. Transfer", 
                   command=self.transfer).pack(side=tk.LEFT, padx=(0, 10))
        
        
        ttk.Button(button_frame, text="Preview Cleanup", 
                  command=self.preview_cleanup).pack(side=tk.LEFT)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(20, 10))
        
        # Status text
        self.status_text = tk.Text(main_frame, height=10, width=80)
        self.status_text.grid(row=10, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        # Status scrollbar
        status_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        status_scrollbar.grid(row=10, column=3, sticky=(tk.N, tk.S), pady=(10, 0))
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
        
        # Configure grid weights for resizing
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(10, weight=2)
        
    def add_folder(self):
        folder = filedialog.askdirectory(title="Select folder to process")
        if folder and folder not in self.selected_folders:
            self.selected_folders.append(folder)
            self.folder_listbox.insert(tk.END, folder)
            self.log(f"Added folder: {folder}")
    
    def remove_selected_folder(self):
        selection = self.folder_listbox.curselection()
        if selection:
            index = selection[0]
            folder = self.selected_folders.pop(index)
            self.folder_listbox.delete(index)
            self.log(f"Removed folder: {folder}")
    
    def clear_all_folders(self):
        self.selected_folders.clear()
        self.folder_listbox.delete(0, tk.END)
        self.log("Cleared all folders")
    
    def log(self, message):
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()
    
    def find_empty_dirs(self, path: str) -> Set[str]:
        """Find all empty directories in the given path (recursive)"""
        empty_dirs = set()
        
        for root, dirs, files in os.walk(path, topdown=False):
            # Check if directory is empty (no files and no non-empty subdirs)
            if not files and not dirs:
                empty_dirs.add(root)
            elif not files:
                # Check if all subdirectories are empty
                all_subdirs_empty = all(
                    os.path.join(root, d) in empty_dirs for d in dirs
                )
                if all_subdirs_empty:
                    empty_dirs.add(root)
        
        return empty_dirs
    
    def remove_empty_dirs(self, path: str, dry_run: bool = False) -> List[str]:
        """Remove empty directories, return list of removed directories"""
        removed = []
        max_iterations = 10  # Prevent infinite loops
        
        for _ in range(max_iterations):
            empty_dirs = self.find_empty_dirs(path)
            if not empty_dirs:
                break
                
            for empty_dir in sorted(empty_dirs, key=len, reverse=True):
                try:
                    if not dry_run:
                        os.rmdir(empty_dir)
                    removed.append(empty_dir)
                    self.log(f"{'[DRY RUN] Would remove' if dry_run else 'Removed'} empty directory: {empty_dir}")
                except OSError as e:
                    self.log(f"Error removing {empty_dir}: {str(e)}")
        
        return removed
    
    def preview_cleanup(self):
        if not self.selected_folders:
            messagebox.showwarning("Warning", "Please select at least one folder")
            return
        
        self.log("\n=== PREVIEW CLEANUP (DRY RUN) ===")
        for folder in self.selected_folders:
            if os.path.exists(folder):
                self.log(f"\nScanning: {folder}")
                removed = self.remove_empty_dirs(folder, dry_run=True)
                if not removed:
                    self.log("No empty directories found")
            else:
                self.log(f"Folder not found: {folder}")
        self.log("\n=== PREVIEW COMPLETE ===\n")
    
    def clean_folders_only(self):
        if not self.selected_folders:
            messagebox.showwarning("Warning", "Please select at least one folder")
            return
        
        def cleanup_thread():
            try:
                self.progress.start()
                self.log("\n=== STARTING FOLDER CLEANUP ===")
                
                total_removed = []
                for folder in self.selected_folders:
                    if os.path.exists(folder):
                        self.log(f"\nCleaning: {folder}")
                        removed = self.remove_empty_dirs(folder)
                        total_removed.extend(removed)
                    else:
                        self.log(f"Folder not found: {folder}")
                
                self.removed_folders = total_removed
                self.log(f"\n=== CLEANUP COMPLETE ===")
                self.log(f"Total empty directories removed: {len(total_removed)}")
                
            except Exception as e:
                self.log(f"Error during cleanup: {str(e)}")
                messagebox.showerror("Error", f"Cleanup failed: {str(e)}")
            finally:
                self.progress.stop()
        
        threading.Thread(target=cleanup_thread, daemon=True).start()
    
    def clean_and_transfer(self):
        if not self.selected_folders:
            messagebox.showwarning("Warning", "Please select at least one folder")
            return
        
        host = self.host_entry.get().strip()
        remote_path = self.path_entry.get().strip()
        
        if not remote_path:
            messagebox.showwarning("Warning", "Please enter both remote host and path")
            return
        
        def transfer_thread():
            try:
                self.progress.start()
                
                # First clean the folders
                self.log("\n=== STARTING FOLDER CLEANUP ===")
                total_removed = []
                valid_folders = []
                
                for folder in self.selected_folders:
                    if os.path.exists(folder):
                        self.log(f"\nCleaning: {folder}")
                        removed = self.remove_empty_dirs(folder)
                        total_removed.extend(removed)
                        valid_folders.append(folder)
                    else:
                        self.log(f"Folder not found: {folder}")
                
                self.removed_folders = total_removed
                self.log(f"\nCleanup complete. Removed {len(total_removed)} empty directories")
                
                # Then transfer via SCP
                if valid_folders:
                    self.log("\n=== STARTING SCP TRANSFER ===")
                    
                    for folder in valid_folders:
                        self.log(f"\nTransferring: {folder}")
                        
                        # Build SCP command
                        cmd = ["scp", '-v']
                        if self.recursive_var.get():
                            cmd.append("-r")
                        if self.preserve_var.get():
                            cmd.append("-p")
                        
                        cmd.extend([folder, f"{remote_path}"])
                        
                        self.log(f"Running: {' '.join(cmd)}")
                        
                        # Execute SCP
                        try:
                            result = subprocess.run(
                                cmd, 
                                capture_output=True, 
                                text=True, 
                                timeout=300  # 5 minute timeout
                            )
                            
                            if result.returncode == 0:
                                self.log(f"✓ Successfully transferred: {os.path.basename(folder)}")
                                if result.stdout:
                                    self.log(f"Output: {result.stdout.strip()}")
                            else:
                                self.log(f"✗ Transfer failed for: {os.path.basename(folder)}")
                                self.log(f"Error: {result.stderr.strip()}")
                                
                        except subprocess.TimeoutExpired:
                            self.log(f"✗ Transfer timed out for: {os.path.basename(folder)}")
                        except Exception as e:
                            self.log(f"✗ Error transferring {os.path.basename(folder)}: {str(e)}")
                    
                    self.log("\n=== TRANSFER COMPLETE ===")
                else:
                    self.log("No valid folders to transfer")
                    
            except Exception as e:
                self.log(f"Error during process: {str(e)}")
                messagebox.showerror("Error", f"Process failed: {str(e)}")
            finally:
                self.progress.stop()
        
        # Confirm before starting
        result = messagebox.askyesno(
            "Confirm Transfer",
            f"This will:\n1. Clean empty directories from {len(self.selected_folders)} folders\n"
            f"2. Transfer cleaned folders to {host}:{remote_path}\n\nProceed?"
        )
        
        if result:
            threading.Thread(target=transfer_thread, daemon=True).start()


    def transfer(self):
        if not self.selected_folders:
            messagebox.showwarning("Warning", "Please select at least one folder")
            return
        
        host = self.host_entry.get().strip()
        remote_path = self.path_entry.get().strip()
        
        if not remote_path:
            messagebox.showwarning("Warning", "Please enter both remote host and path")
            return
        
        def transfer_thread():


            try:
                    self.progress.start()
            
                    # Then transfer via SCP
                    self.log("\n=== STARTING SCP TRANSFER ===")
                    
                    for folder in self.selected_folders:
                        self.log(f"\nTransferring: {folder}")
                        
                        # Build SCP command
                        cmd = ["scp", '-v']
                        if self.recursive_var.get():
                            cmd.append("-r")
                        if self.preserve_var.get():
                            cmd.append("-p")
                        
                        cmd.extend([folder, f"{remote_path}"])
                        
                        self.log(f"Running: {' '.join(cmd)}")
                        
                        # Execute SCP
                        try:
                            result = subprocess.run(
                                cmd, 
                                capture_output=True, 
                                text=True, 
                                timeout=300  # 5 minute timeout
                            )
                            
                            if result.returncode == 0:
                                self.log(f"✓ Successfully transferred: {os.path.basename(folder)}")
                                if result.stdout:
                                    self.log(f"Output: {result.stdout.strip()}")
                            else:
                                self.log(f"✗ Transfer failed for: {os.path.basename(folder)}")
                                self.log(f"Error: {result.stderr.strip()}")
                                
                        except subprocess.TimeoutExpired:
                            self.log(f"✗ Transfer timed out for: {os.path.basename(folder)}")
                        except Exception as e:
                            self.log(f"✗ Error transferring {os.path.basename(folder)}: {str(e)}")
                    
                    self.log("\n=== TRANSFER COMPLETE ===")
                    
            except Exception as e:
                self.log(f"Error during process: {str(e)}")
                messagebox.showerror("Error", f"Process failed: {str(e)}")
            finally:
                self.progress.stop()
        
        # Confirm before starting
        result = messagebox.askyesno(
            "Confirm Transfer",
            f"This will:\n1. Clean empty directories from {len(self.selected_folders)} folders\n"
            f"2. Transfer cleaned folders to {host}:{remote_path}\n\nProceed?"
        )
        
        if result:
            threading.Thread(target=transfer_thread, daemon=True).start()

def main():
    root = tk.Tk()
    app = FolderCleanupSCP(root)
    root.mainloop()


if __name__ == "__main__":
    main()
