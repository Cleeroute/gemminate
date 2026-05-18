import re

with open('templates/dashboard.html', 'r') as f:
    html = f.read()

html = re.sub(
    r"// Show stop button if generating\s+if \(!document\.getElementById\('stop-generation-btn'\)\) \{[\s\S]*?lucide\.createIcons\(\);\s+\}",
    r"",
    html
)

html = re.sub(
    r"const stopBtn = document\.getElementById\('stop-generation-btn'\);\s+if \(stopBtn\) stopBtn\.remove\(\);",
    r"const submitBtn = document.querySelector('#chat-form button[type=\"submit\"]');\n                        if (submitBtn) {\n                            submitBtn.disabled = false;\n                            submitBtn.classList.remove('opacity-50', 'cursor-not-allowed', 'bg-red-500', 'hover:bg-red-600', 'is-generating');\n                            submitBtn.classList.add('bg-black', 'hover:bg-gray-800');\n                            submitBtn.innerHTML = '<i data-lucide=\"arrow-up\" class=\"w-4 h-4\"></i>';\n                            lucide.createIcons();\n                        }",
    html
)

with open('templates/dashboard.html', 'w') as f:
    f.write(html)
print("done")
