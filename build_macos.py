import PyInstaller.__main__
import os
import shutil
import sys
import unicodeitplus
import matplotlib

# --- CONFIGURATION ---
ICON_FILENAME = "icon.png"
APP_NAME = "LaTeX-Inserter"
PLIST_FILENAME = "Info.plist"

# --- Step 1: Clean up old build files ---
print("Cleaning up old build directories...")
for folder in ['build', 'dist', f'{APP_NAME}.spec']:
    if os.path.exists(folder):
        try:
            if os.path.isdir(folder):
                shutil.rmtree(folder)
            else:
                os.remove(folder)
            print(f"Removed old '{folder}'.")
        except OSError as e:
            print(f"Error removing {folder}: {e}")
            sys.exit(1)

# --- Step 2: Validate that necessary files exist ---
if not os.path.exists(ICON_FILENAME):
    print(f"ERROR: '{ICON_FILENAME}' not found. Please add it to the project folder.")
    sys.exit(1)
if not os.path.exists(PLIST_FILENAME):
    print(f"ERROR: '{PLIST_FILENAME}' not found. Please add it to the project folder.")
    sys.exit(1)


# --- Step 3: Dynamically find paths for data ---
separator = ':'
unicode_path = unicodeitplus.__path__[0]
add_data_unicode = f'{unicode_path}{separator}unicodeitplus'
print(f"Found unicodeitplus data at: {unicode_path}")

mpl_data_path = matplotlib.get_data_path()
add_data_matplotlib = f'{mpl_data_path}{separator}matplotlib/mpl-data'
print(f"Found matplotlib data at: {mpl_data_path}")

add_data_icon = f'{ICON_FILENAME}{separator}.'
print(f"Will bundle '{ICON_FILENAME}'.")

# THE FIX: We also bundle the Info.plist as a data file.
# PyInstaller's macOS hooks will find and use it.
add_data_plist = f'{PLIST_FILENAME}{separator}.'
print(f"Will bundle '{PLIST_FILENAME}' for app metadata.")


# --- Step 4: Run the PyInstaller Build Command for macOS ---
print("\nStarting PyInstaller build for macOS...")
try:
    PyInstaller.__main__.run([
        'main.py',
        f'--name={APP_NAME}',
        '--onefile',
        '--windowed',
        f'--icon={ICON_FILENAME}',
        f'--add-data={add_data_unicode}',
        f'--add-data={add_data_matplotlib}',
        f'--add-data={add_data_icon}',
        # THIS IS THE CORRECTED WAY TO INCLUDE THE PLIST
        f'--add-data={add_data_plist}',
        '--clean',
        f'--osx-bundle-identifier=com.yourname.latexinserter',
    ])
    print(f"\nBuild complete! The '{APP_NAME}.app' bundle is in the 'dist' folder.")

except Exception as e:
    print(f"\nAn error occurred during the build process: {e}")
