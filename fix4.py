import re

with open('templates/dashboard.html', 'r') as f:
    content = f.read()

content = re.sub(
    r"if \(actionType === 'video' && message\.trim\(\) === '@video'\) \{",
    r"if (actionType === 'video' && message.trim().match(/^(\\d+)?@video$/i)) {",
    content
)

with open('templates/dashboard.html', 'w') as f:
    f.write(content)
