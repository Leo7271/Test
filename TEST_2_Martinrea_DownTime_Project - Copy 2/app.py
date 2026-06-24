"""Wrapper launcher to run the actual app inside DownTime_Project_Test_2.
This lets you run `python app.py` from the workspace root.
"""
import os
import runpy
import sys

def main():
    base = os.path.dirname(__file__)
    target = os.path.join(base, 'DownTime_Project_Test_2', 'app.py')
    if not os.path.exists(target):
        print(f"ERROR: target file not found: {target}")
        sys.exit(2)
    # Run the target as a script (so __name__ == '__main__' inside it)
    runpy.run_path(target, run_name='__main__')

if __name__ == '__main__':
    main()
