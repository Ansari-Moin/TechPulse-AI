import os
import subprocess
import feedparser
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# =========================
# CONFIGURATION
# =========================

NEWS_FOLDER = os.path.join(
    os.path.expanduser("~"),
    "Documents",
    "TechPulseAI"
)
OLLAMA_MODEL = "llama3.2:3b"

RSS_FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "NVIDIA Blog": "https://blogs.nvidia.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "The Verge": "https://www.theverge.com/rss/index.xml"
}

KEYWORDS = [
    "python", "c++", "ai", "machine learning",
    "mlops", "devops", "nvidia", "gpu", "architecture"
]

# =========================
# WINDOWS NOTIFICATION (SAFE)
# =========================

def windows_notify(title, message):
    ps_script = f'''
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
    $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
    $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
    $text = $xml.GetElementsByTagName("text")
    $text.Item(0).AppendChild($xml.CreateTextNode("{title}")) > $null
    $text.Item(1).AppendChild($xml.CreateTextNode("{message}")) > $null
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Personalized News Fetcher").Show($toast)
    '''
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

# =========================
# RSS NEWS FETCHING
# =========================

def fetch_recent_news():
    six_months_ago = datetime.now() - timedelta(days=180)
    articles = []

    for source, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)

        for entry in feed.entries:
            if not hasattr(entry, "published_parsed"):
                continue

            published = datetime(*entry.published_parsed[:6])
            if published < six_months_ago:
                continue

            title_lower = entry.title.lower()
            if any(k in title_lower for k in KEYWORDS):
                articles.append(
                    f"{entry.title}\n{entry.link}\n({source}, {published.date()})\n"
                )

    return articles

# =========================
# OLLAMA HANDLING
# =========================

def ensure_ollama_running():
    try:
        subprocess.run(
            ["ollama", "list"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5
        )
    except:
        subprocess.Popen(
            ["ollama"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

def summarize_text(text):
    try:
        prompt = (
            "Summarize the following tech news into concise bullet points:\n\n"
            + text
        )

        result = subprocess.run(
            ["ollama", "run", OLLAMA_MODEL, prompt],
            text=True,
            capture_output=True,
            timeout=180
        )

        if result.returncode != 0 or not result.stdout.strip():
            return "AI summarization unavailable."

        return result.stdout.strip()

    except Exception:
        return "AI summarization unavailable."

# =========================
# PDF GENERATION
# =========================

def create_pdf(text):
    os.makedirs(NEWS_FOLDER, exist_ok=True)

    filename = f"news_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.pdf"
    full_path = os.path.join(NEWS_FOLDER, filename)

    c = canvas.Canvas(full_path, pagesize=letter)
    width, height = letter

    y = height - 50
    c.setFont("Helvetica", 11)

    for line in text.split("\n"):
        c.drawString(40, y, line[:100])
        y -= 14
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - 50

    c.save()
    return full_path

# =========================
# MAIN
# =========================

def main():
    print("Fetching recent articles...")
    articles = fetch_recent_news()

    if not articles:
        print("No relevant articles found.")
        windows_notify(
            "News PDF Ready",
            "Your personalized tech news PDF has been generated."
        )
        return

    ensure_ollama_running()

    print("Summarizing with local AI...")
    combined_text = "\n".join(articles)
    summary = summarize_text(combined_text)

    print("Creating PDF...")
    pdf_path = create_pdf(summary)

    windows_notify(
        "News PDF Ready",
        "Your personalized tech news PDF has been generated."
    )
    os.startfile(pdf_path)
    print(f"Done! PDF saved: {pdf_path}")

if __name__ == "__main__":
    main()
