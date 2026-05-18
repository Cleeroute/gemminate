import re

with open('templates/dashboard.html', 'r') as f:
    html = f.read()

# 1. Stop button logic
html = re.sub(
    r"input\.disabled = true;\s+submitBtn\.disabled = true;\s+submitBtn\.classList\.add\('opacity-50', 'cursor-not-allowed'\);",
    r"input.disabled = true;\n            submitBtn.innerHTML = '<i data-lucide=\"square\" class=\"w-4 h-4 fill-current\"></i>';\n            submitBtn.classList.remove('bg-black', 'hover:bg-gray-800');\n            submitBtn.classList.add('bg-red-500', 'hover:bg-red-600', 'is-generating');\n            lucide.createIcons();",
    html
)

html = re.sub(
    r"// Show stop button\s+if \(!document\.getElementById\('stop-generation-btn'\)\) \{[\s\S]*?lucide\.createIcons\(\);\s+\}",
    r"",
    html
)

html = re.sub(
    r"const submitBtn = document\.querySelector\('#chat-form button\[type=\"submit\"\]'\);\s+input\.disabled = false;\s+submitBtn\.classList\.remove\('opacity-50', 'cursor-not-allowed'\);\s+const stopBtn = document\.getElementById\('stop-generation-btn'\);\s+if \(stopBtn\) stopBtn\.remove\(\);",
    r"const submitBtn = document.querySelector('#chat-form button[type=\"submit\"]');\n            input.disabled = false;\n            submitBtn.disabled = false;\n            submitBtn.classList.remove('opacity-50', 'cursor-not-allowed', 'bg-red-500', 'hover:bg-red-600', 'is-generating');\n            submitBtn.classList.add('bg-black', 'hover:bg-gray-800');\n            submitBtn.innerHTML = '<i data-lucide=\"arrow-up\" class=\"w-4 h-4\"></i>';\n            lucide.createIcons();",
    html
)

# Fix the submit handler to stop if generating
html = html.replace(
    "let message = input.value.trim();",
    "if (submitBtn.classList.contains('is-generating')) {\n                stopGeneration();\n                return;\n            }\n            let message = input.value.trim();"
)

# Write back
with open('templates/dashboard.html', 'w') as f:
    f.write(html)
print("done")
