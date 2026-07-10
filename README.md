[![CI/CD](https://github.com/zarvelionzynji/homehub/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/zarvelionzynji/homehub/actions/workflows/docker-publish.yml)
![Latest Release](https://img.shields.io/github/v/release/zarvelionzynji/homehub?include_prereleases)
[![GitHub last commit](https://img.shields.io/github/last-commit/zarvelionzynji/homehub)](https://github.com/zarvelionzynji/homehub/commits/main)

# 🏡 HomeHub (Fork)

> **Fork Info**: This project is a modified fork of the original [HomeHub by surajverma](https://github.com/surajverma/homehub).

HomeHub is a lightweight self-hosted web application designed to be the digital hub for your household's daily activities.

## ✨ Key Features
* **🔗 Quick Links**: Visual grid-style dashboard for organizing family bookmarks and favorite links, complete with icon logos and smart category grouping.
* **📝 Shared Notes & Cloud**: A simple space for quick notes and file sharing on your home network.
* **🛒 Shopping List & Chores**: Collaborative lists for tracking groceries and household tasks.
* **🗓️ Calendar & Reminders**: A shared calendar for important dates and recurring reminders.
* **💰 Expense Tracker**: Track family expenses and monthly bills (supports paid/unpaid status).
* **🚗 Vehicle Maintenance Log**: Log service records for vehicles (cars & motorcycles) with odometer, costs, and attachments. Includes automatic service alerts and bidirectional cost sync with the Expense Tracker.
* **👋 Who's Home?**: Quickly check which family members are currently home.
* **🎬 Media Downloader**: Save videos or music directly to your server.
* **🤖 AI Agent API (RESTful)**: Connect HomeHub with your favorite AI assistants (like OpenClaw or GPT). AI can manage home status, read notes, complete chores, and even modify `config.yml` programmatically via an authenticated API.
* **🌐 Multi-Language (EN/ID)**: Supports two languages — English and Indonesian. Language switcher in the header to toggle anytime.
* **📱 Mobile Responsive**: Compact single-row header on mobile devices, all features remain easily accessible.
* **🔒 Full Privacy**: All your data stays on your own network. No third-party tracking.

## 🚀 Quick Start with Docker

1. Clone this repository and create a config copy:
```bash
git clone https://github.com/zarvelionzynji/homehub.git
cd homehub
cp config-example.yml config.yml
```

2. Open and edit `config.yml` to set family member names and other settings.

3. Run with Docker Compose:
```bash
docker compose up -d
```
Your HomeHub is ready at [http://localhost:5000](http://localhost:5000).

## 🛠️ Development Setup

To run locally without Docker for code changes:
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
pip install -r requirements.txt
npm install
npm run build:css

python run.py
```

## 📜 License & Disclaimer

This project is licensed under the MIT License.
This software is provided "as is" without warranty. Designed for use on **trusted local networks** and not recommended for direct exposure to the public internet without additional security measures.
