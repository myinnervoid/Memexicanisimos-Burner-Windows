import re

with open("src/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix str(e)
content = content.replace("self.after(0, self.on_error, str(e))", "self.after(0, self.on_error, str(exc))")

# Fix {exc}
content = content.replace("format(err=exc)", "format(exc=exc)")

with open("src/main.py", "w", encoding="utf-8") as f:
    f.write(content)
