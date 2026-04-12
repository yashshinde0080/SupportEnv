import os
import filecmp

def compare_dirs(dir1, dir2):
    dcmp = filecmp.dircmp(dir1, dir2, ignore=['.git', '__pycache__', '.pytest_cache', '.venv', 'support_env.egg-info', '.agents', '.claude'])
    diff = []
    if dcmp.diff_files:
        diff.extend([(f, "File content differs") for f in dcmp.diff_files])
    if dcmp.left_only:
        diff.extend([(f, "Only in dir1") for f in dcmp.left_only])
    if dcmp.right_only:
        diff.extend([(f, "Only in dir2") for f in dcmp.right_only])
    
    for sub in dcmp.common_dirs:
        diff.extend([(f"{sub}/{f}", msg) for f, msg in compare_dirs(os.path.join(dir1, sub), os.path.join(dir2, sub))])
    return diff

diffs = compare_dirs(r"d:\SupportEnv", r"d:\SupportEnv\SupportEnv\SupportEnv")
for f, msg in diffs:
    print(f"{msg}: {f}")
print("Done")
