with open('templates/dashboard.html', 'r') as f:
    content = f.read()

content = content.replace(
"""            const submitBtn = document.querySelector('#chat-form button[type="submit"]');
            input.disabled = false;
            input.placeholder = "Ask Gemminate anything...";
            submitBtn.disabled = false;
            submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            const submitBtn = document.querySelector('#chat-form button[type=\\"submit\\"]');
                        if (submitBtn) {
                            submitBtn.disabled = false;
                            submitBtn.classList.remove('opacity-50', 'cursor-not-allowed', 'bg-red-500', 'hover:bg-red-600', 'is-generating');
                            submitBtn.classList.add('bg-black', 'hover:bg-gray-800');
                            submitBtn.innerHTML = '<i data-lucide=\\"arrow-up\\" class=\\"w-4 h-4\\"></i>';
                            lucide.createIcons();
                        }""",
"""            const submitBtn = document.querySelector('#chat-form button[type="submit"]');
            input.disabled = false;
            input.placeholder = "Ask Gemminate anything...";
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.classList.remove('opacity-50', 'cursor-not-allowed', 'bg-red-500', 'hover:bg-red-600', 'is-generating');
                submitBtn.classList.add('bg-black', 'hover:bg-gray-800');
                submitBtn.innerHTML = '<i data-lucide="arrow-up" class="w-4 h-4"></i>';
                lucide.createIcons();
            }"""
)

with open('templates/dashboard.html', 'w') as f:
    f.write(content)
