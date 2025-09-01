import os
import re
import time
import requests
import google.generativeai as genai
from urllib.parse import urljoin, urlparse
from pyfiglet import Figlet
from termcolor import colored
from colorama import init

# Initialize colorama
init(autoreset=True)

# ================== BANNER ==================
def show_banner():
    f = Figlet(font="slant")
    banner = f.renderText("KeyHound")
    print(colored(banner, "red", attrs=["bold"]))
    print(colored("🐺  The Hunter of Exposed Keys & Secrets  🐺", "yellow", attrs=["bold"]))
    print(colored("-" * 70, "cyan"))
    print(colored("⚡ Made by Aryan Giri ⚡", "magenta", attrs=["bold", "blink"]))
    print(colored("=" * 70, "cyan"))

# ================== LOAD GEMINI KEY ==================
def load_api_key():
    if not os.path.exists("key.txt"):
        print(colored("⚠  key.txt not found! Please create a file with your Gemini API key.", "red"))
        exit(1)
    with open("key.txt", "r", encoding="utf-8") as f:
        key = f.read().strip()
    if not key:
        print(colored("⚠  key.txt is empty! Add your Gemini API key.", "red"))
        exit(1)
    return key

# ================== CONFIG ==================
TARGET_EXTENSIONS = [
    ".js", ".ts", ".jsx", ".tsx",
    ".php",
    ".py",
    ".rb",
    ".java", ".kt",
    ".cs",
    ".go",
    ".swift", ".m",
    ".env",
    ".json",
    ".yaml", ".yml",
    ".git-credentials"
]

PATH_PATTERN = re.compile(r'([a-zA-Z0-9_\-./]+(?:\.[a-z]+))')

visited_urls = set()
session = requests.Session()

# ================== AI ANALYSIS ==================
def ai_analyze(line, url, line_no, model):
    prompt = f"""
    You are KeyHound 🐺 scanning for exposed API keys.

    URL: {url}
    Line: {line_no}

    Line Content:
    {line}

    Tasks:
    1. Does this line contain an API key, secret, or token? (Yes/No)
    2. If Yes, which service/provider might it belong to?
    3. Sensitivity level? (Low/Medium/High)
    4. Does this line reference another file or directory path worth scanning? (Yes/No). If yes, extract the path.

    Keep it concise.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"AI analysis failed: {e}"

# ================== PATH EXTRACTION ==================
def extract_paths(line, base_url):
    matches = PATH_PATTERN.findall(line)
    resolved = []
    for m in matches:
        full_url = urljoin(base_url, m)
        parsed = urlparse(full_url)
        if any(parsed.path.endswith(ext) for ext in TARGET_EXTENSIONS):
            resolved.append(full_url)
    return resolved

# ================== SCAN URL ==================
def scan_url(url, delay, model):
    findings = []
    if url in visited_urls:
        return findings
    visited_urls.add(url)

    print(colored(f"\n📡 Scanning: {url}", "cyan", attrs=["bold"]))

    try:
        r = session.get(url, timeout=10)
        if r.status_code != 200 or not r.text.strip():
            print(colored(f"⚠ Skipped (status {r.status_code})", "yellow"))
            return findings

        for line_no, line in enumerate(r.text.splitlines(), start=1):
            if not line.strip():
                continue

            # AI analysis
            ai_result = ai_analyze(line.strip(), url, line_no, model)
            if "Yes" in ai_result:
                finding = f"[{url}:{line_no}] {line.strip()}\n→ {ai_result}\n"
                findings.append(finding)
                print(colored("🔥 Possible secret found!", "red", attrs=["bold"]))
                print(colored(finding, "green"))

            # Path discovery
            new_paths = extract_paths(line, url)
            for np in new_paths:
                findings.extend(scan_url(np, delay, model))

            time.sleep(delay)

    except Exception as e:
        print(colored(f"⚠ Error fetching {url}: {e}", "red"))
    return findings

# ================== MAIN ==================
if __name__ == "__main__":
    show_banner()

    api_key = load_api_key()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    start_url = input(colored("Enter target URL: ", "yellow")).strip()
    delay = float(input(colored("Enter delay per request (seconds): ", "yellow")).strip())

    # Ask for cookies
    use_cookies = input(colored("Do you want to use cookies? (y/n): ", "yellow")).strip().lower()
    if use_cookies == "y":
        raw_cookie = input(colored("Enter cookies (key=value; key2=value2): ", "yellow")).strip()
        cookie_dict = {}
        for part in raw_cookie.split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1)
                cookie_dict[key] = value
        session.cookies.update(cookie_dict)
        print(colored(f"✅ Cookies added: {cookie_dict}", "green"))
    else:
        print(colored("⚠ No cookies set, scanning as unauthenticated user.", "yellow"))

    results = scan_url(start_url, delay, model)

    print(colored("\n" + "="*70, "cyan"))
    if results:
        print(colored("⚠ Possible API keys or sensitive paths found:\n", "red", attrs=["bold"]))
        for r in results:
            print(colored(r, "green"))

        save_choice = input(colored("\nDo you want to save the output? (y/n): ", "yellow")).strip().lower()
        if save_choice == "y":
            filename = input(colored("Enter filename (default: KeyHound_Report.txt): ", "yellow")).strip()
            if not filename:
                filename = "KeyHound_Report.txt"
            with open(filename, "w", encoding="utf-8") as out:
                out.write("\n".join(results))
                out.write("\n\n" + "="*50 + "\n")
                out.write("⚡ Report generated by KeyHound 🐺\n")
                out.write("⚡ Made by Aryan Giri ⚡\n")
            print(colored(f"\n📂 Report saved to {filename}", "green", attrs=["bold"]))
        else:
            print(colored("\n✅ Output not saved, only displayed on screen.", "yellow"))
    else:
        print(colored("✅ No secrets found at target.", "green", attrs=["bold"]))
                                                                                    
