with open('templates/dashboard.html', 'r') as f:
    content = f.read()

content = content.replace(
"""                        const percent = Math.round((current / total) * 100);""",
"""                        const percent = Math.min(100, Math.round((current / Math.max(1, total)) * 100));"""
)

with open('templates/dashboard.html', 'w') as f:
    f.write(content)
