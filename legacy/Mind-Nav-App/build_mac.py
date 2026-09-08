import os
import subprocess
import shutil

# Build script for Mind-Nav BCI Suite (macOS)

print("🚀 Building Mind-Nav BCI Suite for macOS...")

# Ensure dist directory exists
if not os.path.exists("dist"):
    os.makedirs("dist")

# Run PyInstaller
cmd = [
    "pyinstaller",
    "--name", "Mind-Nav BCI Suite",
    "--windowed",                 # No console window
    "--onedir",                   # Bundle as a .app directory (standard for macOS)
    "--icon", "../Media/Mind-Nav-Logo.icns",
    "--add-data", "../Media/Mind-Nav-Logo.png:Media",
    "--add-data", "../Notebook/*.pt:Notebook",
    "--add-data", "../Notebook/*.joblib:Notebook",
    "--noconfirm",                # Overwrite existing build
    "main.py"
]

subprocess.run(cmd, check=True)

print("✅ Build complete! Executable is at dist/Mind-Nav BCI Suite.app")
