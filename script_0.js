
        window.MathJax = {
            tex: {
                inlineMath: [['\\(', '\\)'], ['$', '$']],
                displayMath: [['\\[', '\\]'], ['$$', '$$']]
            },
            options: {
                skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
            }
        };
        // Configure marked to not mangle math blocks by treating them as custom inline/block tokens
        const mathExtension = {
            name: 'math',
            level: 'inline',
            start(src) { return src.match(/\$|\\\(|\\\[|\[/)?.index; },
            tokenizer(src, tokens) {
                // Improved regex to handle various delimiters including those without backslashes sometimes used by LLMs
                const match = src.match(/^(\$\$|\\\[)([\s\S]*?)(\$\$|\\\])/) || 
                              src.match(/^(\\\[)([\s\S]*?)(\\\])/) ||
                              src.match(/^(\$|\\\()(.*?)(\$|\\\))/);
                
                if (match) {
                    return {
                        type: 'math',
                        raw: match[0],
                        text: match[2]
                    };
                }
            },
            renderer(token) {
                return token.raw;
            }
        };
        marked.use({ extensions: [mathExtension] });
    