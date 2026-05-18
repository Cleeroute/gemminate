import subprocess
import os

with open("test_syntax.js", "w") as f:
    f.write(open("script_1.js").read())

result = subprocess.run(["node", "-c", "test_syntax.js"], capture_output=True, text=True)
print("Return code:", result.returncode)
print("Stdout:", result.stdout)
print("Stderr:", result.stderr)
