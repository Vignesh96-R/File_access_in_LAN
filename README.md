# LAN Network File Share

A web-based file sharing and management tool for local area networks (LAN), built with Flask. This project allows users to browse, preview, upload, download, and manage files on a shared directory over the LAN.

## Features
- Browse files and directories on a shared folder
- Preview images, videos, audio, PDFs, MHTML, and text/code files in-browser
- Download and upload files
- Delete files (with confirmation)
- Filter and search files by type, name, or extension
- Responsive web interface for easy navigation

## Project Structure (after refactor)
- `backserver.py` — Main Flask application logic
- `templates/` — HTML templates for rendering web pages
- `static/` — Static files (CSS, JS, images)

## Installation
1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd File_access_in_LAN
   ```
2. **Install dependencies:**
   ```bash
   pip install flask
   ```

## Usage
1. **Run the server:**
   ```bash
   python backserver.py
   ```
2. **Access the web interface:**
   Open your browser and go to `http://<your-local-ip>:5000/`

   (The local IP will be shown in the terminal when you start the server.)

## Notes
- Make sure the shared directory is accessible and has the necessary permissions.
- The project will be refactored to use Flask best practices (separating templates and static files).
- For any issues, please open an issue or contact the maintainer.
