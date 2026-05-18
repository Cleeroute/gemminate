import re

with open('templates/dashboard.html', 'r') as f:
    content = f.read()

content = content.replace(
"""                        submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                        
                        const submitBtn = document.querySelector('#chat-form button[type=\"submit\"]');
                        if (submitBtn) {""",
"""                        if (submitBtn) {"""
)

content = content.replace(
"""                submitBtn.disabled = false;
                submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                const submitBtn = document.querySelector('#chat-form button[type=\"submit\"]');
                        if (submitBtn) {""",
"""                if (submitBtn) {"""
)

with open('templates/dashboard.html', 'w') as f:
    f.write(content)
