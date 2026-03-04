# Class Charts Timetable for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

This integration brings your child's Class Charts timetable into Home Assistant as a calendar entity.

## Features
- **Daily Sync:** Fetches a 7-day rolling timetable once every 24 hours.
- **Calendar Entity:** View lessons, teachers, and room numbers directly on your dashboard.
- **Automation Ready:** Trigger morning reminders based on the first lesson of the day.

## Installation

### Method 1: HACS (Recommended)
1. Open **HACS** in Home Assistant.
2. Click the three dots in the top right and select **Custom repositories**.
3. Paste `https://github.com/skid88/Classcharts` and select **Integration** as the category.
4. Click **Add**, then click **Download** on the new Class Charts card.
5. Restart Home Assistant.

### Method 2: Manual
1. Download the `custom_components/classcharts` folder.
2. Copy it into your Home Assistant `/config/custom_components/` directory.
3. Restart Home Assistant.

## Configuration
1. Go to **Settings > Devices & Services**.
2. Click **Add Integration** and search for **Class Charts Timetable**.
3. Enter your Parent account details:
   - **Email:** Your Class Charts login email.
   - **Password:** Your Class Charts login password.
   - **Pupil ID:** See below on how to find this.

## How to find your Pupil ID
The Pupil ID is a unique number for your child. It is **not** the access code provided by the school.
1. Log in to the [Class Charts Parent Website](https://www.classcharts.com/parent/login).
2. Select your child.
3. Look at the URL in your browser. It will look like this: `.../parent/pupil/1234567`.
4. The number at the end (`1234567`) is your **Pupil ID**.
