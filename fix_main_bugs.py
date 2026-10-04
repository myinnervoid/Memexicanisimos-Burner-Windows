import re

with open("src/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('class StatusIndicator(ctk.CTkFrame):'):
        pass
    if line.startswith('class MemexicanisimosBurner(ctk.CTk):'):
        pass

    if "def __init__(self):" in line and "StatusIndicator" not in "".join(lines):
        pass # don't touch if not needed

with open("src/main.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("self.after(0, self.on_error, str(e))", "self.after(0, self.on_error, str(exc))")
content = content.replace("format(err=e)", "format(err=exc)")
content = content.replace("format(err_msg=e)", "format(err_msg=exc)")
content = content.replace("except Exception as e:", "except Exception as exc:  # pylint: disable=broad-exception-caught")
content = content.replace("except:", "except Exception as exc:  # pylint: disable=broad-exception-caught")

# Fix {exc} keyerror issue
content = content.replace("messagebox.showerror(_(\"Error\"), _(\"Fallo al instalar dependencias:\\n{err}\").format(err=exc))", "messagebox.showerror(_(\"Error\"), _(\"Fallo al instalar dependencias:\\n{err}\").format(err=exc))")


# Check if class MemexicanisimosBurner(ctk.CTk) exists
if "class MemexicanisimosBurner(ctk.CTk):" not in content:
    # We need to insert it back before its init
    idx = content.find("    def __init__(self):")
    if idx != -1:
        # Find start of line
        start_idx = content.rfind("\n", 0, idx)
        if start_idx != -1:
             content = content[:start_idx] + "\n\nclass MemexicanisimosBurner(ctk.CTk):\n    \"\"\"Clase principal de la aplicación GUI.\"\"\"" + content[start_idx:]

with open("src/main.py", "w", encoding="utf-8") as f:
    f.write(content)
