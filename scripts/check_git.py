import subprocess
import sys

def run_git(args):
    try:
        res = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=r"c:\SatQuery")
        print(f"=== git {' '.join(args)} ===")
        print("STDOUT:", res.stdout[:2000])
        print("STDERR:", res.stderr[:2000])
    except Exception as e:
        print("Error running git:", e)

if __name__ == "__main__":
    run_git(["status"])
    run_git(["log", "-n", "10", "--oneline"])
    run_git(["diff", "--name-only"])
