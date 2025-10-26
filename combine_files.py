import os
from pathlib import Path

def should_include(path):
    """Check if file should be included"""
    exclude_dirs = {'.git', '__pycache__', 'venv', 'env', '.venv', 'node_modules', '.pytest_cache'}
    exclude_files = {'All_Code.txt', 'combine_files.py'}
    
    # Check if any parent directory is in exclude list
    for parent in path.parents:
        if parent.name in exclude_dirs:
            return False
    
    # Check if file itself should be excluded
    if path.name in exclude_files:
        return False
    
    return True

def combine_all_files(root_dir='.', output_file='All_Code.txt'):
    root = Path(root_dir)
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write("=" * 80 + "\n")
        outfile.write("COMPLETE PROJECT CODE DUMP\n")
        outfile.write("=" * 80 + "\n\n")
        
        # Get all files recursively
        all_files = sorted([f for f in root.rglob('*') if f.is_file() and should_include(f)])
        
        for file_path in all_files:
            relative_path = file_path.relative_to(root)
            
            outfile.write("\n" + "=" * 80 + "\n")
            outfile.write(f"FILE: {relative_path}\n")
            outfile.write("=" * 80 + "\n\n")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read())
                outfile.write("\n\n")
            except Exception as e:
                outfile.write(f"[ERROR READING FILE: {e}]\n\n")
        
        outfile.write("\n" + "=" * 80 + "\n")
        outfile.write("END OF CODE DUMP\n")
        outfile.write("=" * 80 + "\n")
    
    print(f"✓ All files combined into {output_file}")
    print(f"✓ Total files included: {len(all_files)}")

if __name__ == "__main__":
    combine_all_files()
