with open('templates/dashboard.html', 'r') as f:
    content = f.read()

# For image click
content = content.replace(
"""                                    // Add small delay before dispatching to allow UI update
                                    setTimeout(() => {
                                        document.querySelector('#chat-form button[type="submit"]').click();
                                    }, 100);""",
"""                                    // Let the user add additional information before hitting enter
                                    const input = document.getElementById('chat-input');
                                    if (input) input.focus();"""
)

# For crop click
content = content.replace(
"""                                        window.togglePdfCropMode();
                                        btn.remove();
                                        setTimeout(() => {
                                            document.querySelector('#chat-form button[type="submit"]').click();
                                        }, 100);""",
"""                                        window.togglePdfCropMode();
                                        btn.remove();
                                        const input = document.getElementById('chat-input');
                                        if (input) input.focus();"""
)

with open('templates/dashboard.html', 'w') as f:
    f.write(content)
