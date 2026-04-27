import shutil, subprocess, sys

print("npm:", shutil.which("npm"))
print("npx:", shutil.which("npx"))

try:
    import playwright
    print("playwright: installed")
except ImportError:
    print("playwright: not installed")

try:
    import selenium
    print("selenium: installed")
except ImportError:
    print("selenium: not installed")
