import sys

def append_to_file(file_path, content):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    file_path = "content/sutras/anapanasati-sutra.md"
    content = sys.stdin.read()
    append_to_file(file_path, content)
