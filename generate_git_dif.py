import subprocess
import os

def get_diff_vs_head():
    """Returns full diff against HEAD (staged + unstaged)."""
    return subprocess.check_output(["git", "diff", "HEAD"]).decode("utf-8")

def get_untracked_files():
    """Returns a list of untracked (new) files."""
    files = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"]
    ).decode("utf-8").splitlines()
    return [f for f in files if os.path.isfile(f)]

def render_untracked_as_diff(files):
    """Generates diff-style output for untracked files."""
    result = []
    for filepath in files:
        result.append(f"diff --git a/{filepath} b/{filepath}")
        result.append(f"new file mode 100644")
        result.append(f"--- /dev/null")
        result.append(f"+++ b/{filepath}")
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                result.append(f"+{line.rstrip()}")
        result.append("")  # newline between files
    return "\n".join(result)

def write_diff_to_markdown(diff_output, output_path="git_diff_summary.md"):
    with open(output_path, "w") as f:
        f.write("# 🧾 Git Diff Summary (vs HEAD)\n\n")
        f.write("```diff\n")
        f.write(diff_output.strip())
        f.write("\n```\n")
    print(f"✅ Diff written to: {output_path}")

if __name__ == "__main__":
    diff = get_diff_vs_head()
    untracked = get_untracked_files()
    diff += "\n" + render_untracked_as_diff(untracked)
    write_diff_to_markdown(diff)
