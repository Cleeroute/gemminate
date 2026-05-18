import re
import sys
import xml.etree.ElementElement

content = open('templates/dashboard.html').read()
scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)

for i, script in enumerate(scripts):
    with open(f'script_{i}.js', 'w') as f:
        f.write(script)
