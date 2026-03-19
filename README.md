# 🏫 Class Charts for Home Assistant 

![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-Home_Assistant-blue.svg)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A modern, UI-configurable integration that brings your **Class Charts** school timetable and homework tracking directly into Home Assistant. 

---

## 🛠 Features
- 📅 **Native Calendar Support**: Syncs your entire school timetable to the HA Calendar.
- ⚙️ **UI Configuration**: No YAML required. Setup and adjust settings directly in the UI.
- 📝 **Homework Tracking**: Detailed sensors for outstanding, completed, and total tasks.
- 👨‍🏫 **Lesson Monitoring**: Know exactly what lesson is on now and what's coming up next.
- 🔄 **Adjustable Date Range**: Sync 1 to 30 days of lessons via the "Configure" menu.
- ⚙️ **Set Update Interval**:  Configure the data synchronization rate. 

---

## 📦 Installation

### Option 1: HACS (Recommended)
1. Open **HACS** > **Integrations**.
2. Click the three dots (top right) > **Custom repositories**.
3. Paste your Repo URL: `https://github.com/skid88/Classcharts`
4. Category: **Integration**.
5. Download and **Restart** Home Assistant.

### Option 2: Manual
1. Copy the `classcharts` folder to your `/config/custom_components/` directory.
2. **Restart** Home Assistant.

---

## ⚙️ Configuration
1. Go to **Settings** > **Devices & Services**.
2. Click **Add Integration** > Search for **Class Charts**.
3. Enter your **Email**, **Password**, and **Pupil ID**.
4. To change settings later, click **Configure** on the integration card.

---

## 📊 Available Entities

### 🗓️ Calendars
| Entity ID | Description |
| :--- | :--- |
| `calendar.class_charts_timetable` | Your daily school timetable (Lessons, Rooms, Teachers). |
| `calendar.class_charts_homework` | Due dates for all assignments as calendar events. |

### 📝 Homework Sensors
| Entity ID | Description |
| :--- | :--- |
| `sensor.outstanding_homework` | Count of active homework. Includes a list in attributes. |
| `sensor.homework_due` | Count of homework tasks due this week. |
| `sensor.completed_homework` | Total number of tasks marked as completed. |

### 👨‍🏫 Lesson Monitoring
| Entity ID | Description |
| :--- | :--- |
| `sensor.class_charts_current_lesson` | The subject you should be in right now. |
| `sensor.class_charts_next_lesson` | The subject coming up next. |

---

 ![Screenshot](https://github.com/skid88/Classcharts/blob/main/Timetable.png)
 ![Screenshot](https://github.com/skid88/Classcharts/blob/main/homework.png)
---
## 🎨 Dashboard: Homework List
Use a **Markdown Card** to display your assignments beautifully:

```jinja2
## 📝 Outstanding Homework
{% set items = state_attr('sensor.outstanding_homework', 'homework_list') %}
{% if items %}
  {% for hw in items %}
  **{{ hw.title }}** ({{ hw.subject }})
  *Due: {{ hw.due_date }}*
  ***
  {% endfor %}
{% else %}
  All caught up! 🎉
{% endif %}

<p style="text-align: center; color: #555; font-size: 0.8em;">
  Last checked: {{ now().strftime('%H:%M') }}
</p>
```
![Screenshot](https://github.com/skid88/Classcharts/blob/main/homework2.png)
---
## 🤝 Support
If you encounter any issues or have feature requests, please open an [Issue](https://github.com/skid88/Classcharts/issues) on this repository.

---

## 📝 License
This project is for personal use and is not an official Class Charts product.

