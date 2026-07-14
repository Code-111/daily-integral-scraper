import os
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import datetime
import json

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# -----------------------------
# CONFIG
# -----------------------------

DIFFICULTIES = {
    "beginner": True,
    "intermediate": True,
    "advanced": True,
    "expert": True,
}

BASE_URL = "https://dailyintegral.com/play/"

# These come from GitHub Secrets
SERVICE_ACCOUNT_JSON = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


# -----------------------------
# GOOGLE DRIVE SERVICE
# -----------------------------

def get_drive_service():
    if not SERVICE_ACCOUNT_JSON:
        raise RuntimeError("GCP_SERVICE_ACCOUNT_JSON not set")

    info = json.loads(SERVICE_ACCOUNT_JSON)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


# -----------------------------
# SCRAPE + PDF
# -----------------------------

def download_integral(difficulty):
    url = BASE_URL + difficulty
    print(f"Fetching {difficulty} from {url}")

    page = requests.get(url)
    soup = BeautifulSoup(page.text, "html.parser")

    download_link = None
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if ".png" in href.lower() or ".pdf" in href.lower():
            download_link = href
            break

    if not download_link:
        print(f"No download link found for {difficulty}")
        return None

    if download_link.startswith("/"):
        download_link = "https://dailyintegral.com" + download_link

    file_data = requests.get(download_link).content

    today = datetime.date.today().isoformat()
    pdf_filename = f"{difficulty}_{today}.pdf"

    image = Image.open(BytesIO(file_data))
    image.save("temp.png")

    c = canvas.Canvas(pdf_filename, pagesize=letter)
    c.drawImage("temp.png", 50, 300, width=500, preserveAspectRatio=True)
    c.save()

    print(f"Saved PDF: {pdf_filename}")
    return pdf_filename


# -----------------------------
# UPLOAD TO DRIVE
# -----------------------------

def upload_to_drive(service, filename):
    if not DRIVE_FOLDER_ID:
        raise RuntimeError("DRIVE_FOLDER_ID not set")

    file_metadata = {
        "name": filename,
        "parents": [DRIVE_FOLDER_ID],
    }

    media = MediaFileUpload(filename, mimetype="application/pdf")

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id",
    ).execute()

    print(f"Uploaded {filename} to Drive (ID: {uploaded.get('id')})")


# -----------------------------
# MAIN ENTRYPOINT
# -----------------------------

def main():
    print("Running DailyIntegral scraper...")

    drive = get_drive_service()

    for difficulty, enabled in DIFFICULTIES.items():
        if not enabled:
            continue

        pdf = download_integral(difficulty)
        if pdf:
            upload_to_drive(drive, pdf)

    print("Done.")


if __name__ == "__main__":
    main()
