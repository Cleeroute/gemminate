import re
import sys
sys.path.append('venv/lib/python3.10/site-packages')
sys.path.append('venv/lib/python3.11/site-packages')
sys.path.append('venv/lib/python3.12/site-packages')
import esprima

with open('templates/dashboard.html', 'r') as f:
    html = f.read()

scripts = re.findall(r'<script.*?>(.*?)</script>', html, re.DOTALL)
for i, script in enumerate(scripts):
    try:
        esprima.parseScript(script)
    except Exception as e:
        print(f"Error in script {i+1}: {e}")
