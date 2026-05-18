from pypdf import PdfReader

pdf_path = "static/uploads/3_1778925298_Physics.pdf"

try:
    reader = PdfReader(pdf_path)
    with open('toc_output.txt', 'w') as f:
        f.write(str(reader.outline))
except Exception as e:
    with open('toc_output.txt', 'w') as f:
        f.write(str(e))
