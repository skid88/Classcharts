# 🏫 Class Charts for Home Assistant _ Test page

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![Version](https://img.shields.io/badge/version-1.0.5-blue.svg)
![Platform](https://img.shields.io/badge/platform-Home_Assistant-blue.svg)

A professional custom integration that brings your **Class Charts** school timetable and homework tracking directly into Home Assistant. Monitor lessons, track classrooms, see which teacher you have next in real-time,

---

## 🛠 Features
- 📅 **Full Calendar Integration**: Syncs your entire school timetable to the Home Assistant Calendar.
- 👨‍🏫 **Lesson Sensors**: Dedicated entities for `Current Lesson` and `Next Lesson`.
- 📍 **Location Tracking**: View room numbers and building names for every period.
- 📋 **Teacher Info**: See the name of the teacher assigned to each lesson.
- 🎨 **Custom Branding**: Includes built-in icons for a seamless look in your "Devices & Services" list.

---

## 📦 Installation

### Option 1: HACS (Recommended)
1. Open **HACS** in Home Assistant.
2. Click the three dots in the top right and select **Custom repositories**.
3. Paste this URL: `https://github.com/skid88/Classcharts`
4. Select **Integration** as the category and click **Add**.
5. Find "Class Charts Timetable" and click **Download**.
6. **Restart** Home Assistant.

### Option 2: Manual
1. Download the `classcharts` folder from `custom_components/`.
2. Upload it to your Home Assistant `/config/custom_components/` directory.
3. **Restart** Home Assistant.

---

## ⚙️ Configuration
1. Navigate to **Settings** > **Devices & Services**.
2. Click **Add Integration** and search for **Class Charts Timetable**.
3. Enter your login credentials:
   - **Email**: Your Class Charts account email.
   - **Password**: Your Class Charts password.
   - **Pupil ID**: Found on your student profile page.

---

## 📊 Available Sensors

| Sensor | Data Source | Description |
| :--- | :--- | :--- |
| **Homework Outstanding** | `meta.this_week_outstanding_count` | Number of tasks currently due. |
| **Homework Completed** | `meta.this_week_completed_count` | Number of tasks ticked 'yes'. |
| **Homework Total** | `meta.this_week_due_count` | All tasks assigned for the current week. |
| **Current Lesson** | `timetable[0]` | The subject name of the ongoing lesson. |
| **Next Lesson** | `timetable[1]` | The subject name of the upcoming lesson. |
| **Timetable Count** | `len(timetable)` | Total number of lessons scheduled for today. |
| **Class Charts Calendar** | `calendar` platform | Full school schedule visible in HA Calendar. |

## 🚀 New Features (v30 "Weekend-Safe" Edition)
- **Direct API Mapping:** Pulls `this_week` counts directly from the API `meta` block for 100% accuracy with the official app.
- **Crash Protection:** Implements strict length-checks on timetable arrays to prevent `KeyError` during weekends or holidays.
- **Enhanced Sensors:** 6 core sensors plus a full student calendar.
- **Card-Mod Ready:** Optimized unique IDs for easy CSS styling in the dashboard.

---
 ![Screenshot](https://github.com/skid88/Classcharts/blob/main/Timetable.png)

---

## 🤝 Support
If you encounter any issues or have feature requests, please open an [Issue](https://github.com/skid88/Classcharts/issues) on this repository.

---

## 📝 License
This project is for personal use and is not an official Class Charts product.





