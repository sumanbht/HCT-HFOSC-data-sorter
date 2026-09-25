import os
import shutil
import glob
from pathlib import Path
import numpy as np
from astropy.io import fits

def inspect_frame_type(header):
    """
    Classifies HCT HFOSC frames based on standard header keywords.
    """
    exptime = float(header.get('EXPTIME', 0.0))
    obj_name = str(header.get('OBJECT', '')).strip()
    
    # Read comment fields (handling multi-line comments)
    comments = " ".join([str(header[k]) for k in header if 'COMMENT' in k])
    
    # 1. Bias
    if exptime == 0.0:
        return 'bias', 'BIAS'
    
    # 2. Halogen Flats
    if 'Halogen' in obj_name or 'flat' in obj_name.lower():
        grism = 'Gr7' if 'r7' in comments else ('Gr8' if 'r8' in comments else 'Flat')
        return 'flat', f"FLAT_{grism}"
    
    # 3. Calibration Lamps (FeNe / FeHe)
    if 'amp' in obj_name.lower() or 'arc' in obj_name.lower():
        if 'r7' in comments or 'fehe' in obj_name.lower():
            return 'arc', 'ARC_FeHe_Gr7'
        elif 'r8' in comments or 'fene' in obj_name.lower():
            return 'arc', 'ARC_FeNe_Gr8'
        return 'arc', f"ARC_{obj_name}"
    
    # 4. Science Targets
    grism = 'Gr7' if 'r7' in comments else ('Gr8' if 'r8' in comments else 'Unknown')
    clean_obj = "".join(c for c in obj_name if c.isalnum() or c in ('_', '-'))
    return 'science', f"OBJ_{clean_obj}_{grism}"


def organize_hct_data(raw_dir='./raw_data', output_dir='./reduction_workspace'):
    """
    Finds raw files, classifies them, and creates a clean workspace directory.
    """
    raw_path = Path(raw_dir)
    workspace = Path(output_dir)
    
    # Create directory tree
    folders = {
        'bias': workspace / 'calib' / 'bias',
        'flat': workspace / 'calib' / 'flat',
        'arc': workspace / 'calib' / 'arc',
        'science': workspace / 'science',
        'reduced': workspace / 'reduced_2d',
        'spectra_1d': workspace / 'spectra_1d'
    }
    
    for f in folders.values():
        f.mkdir(parents=True, exist_ok=True)

    # Collect all FITS and non-extension raw files
    raw_files = sorted(list(raw_path.glob('*')))
    raw_files = [f for f in raw_files if f.is_file() and not f.name.startswith('.')]
    
    print(f"[*] Found {len(raw_files)} files in '{raw_dir}'. Sorting...")
    
    inventory = {'bias': [], 'flat': [], 'arc': [], 'science': {}}
    
    for filepath in raw_files:
        try:
            with fits.open(filepath, ignore_missing_end=True) as hdul:
                header = hdul[0].header
                category, tag = inspect_frame_type(header)
                
                # Determine new file name
                dest_dir = folders[category]
                ext = '.fits' if not filepath.suffix == '.fits' else ''
                new_filename = f"{tag}_{filepath.stem}{filepath.suffix}{ext}"
                dest_path = dest_dir / new_filename
                
                # Copy file to reduction workspace
                shutil.copy2(filepath, dest_path)
                
                if category == 'science':
                    inventory['science'].setdefault(tag, []).append(dest_path.name)
                else:
                    inventory[category].append(dest_path.name)
                    
        except Exception as e:
            print(f"[!] Warning: Could not read {filepath.name}: {e}")

    # Display summary
    print("\n" + "="*50)
    print(f" WORKSPACE CREATED AT: {workspace.resolve()}")
    print("="*50)
    print(f"• Biases sorted     : {len(inventory['bias'])}")
    print(f"• Flats sorted      : {len(inventory['flat'])}")
    print(f"• Lamp Arcs sorted  : {len(inventory['arc'])}")
    print(f"• Science groupings : {len(inventory['science'])}")
    for target_group, files in inventory['science'].items():
        print(f"   -> {target_group} ({len(files)} frame(s))")
    print("="*50 + "\n")
    
    return workspace, inventory

if __name__ == '__main__':
    # Execution entry point
    raw_input_path = input("Enter path to raw HFOSC data directory [default: .]: ").strip() or "."
    workspace_path = input("Enter output workspace directory [default: ./workspace]: ").strip() or "./workspace"
    
    organize_hct_data(raw_input_path, workspace_path)