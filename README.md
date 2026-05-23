# 🏫 Class Charts for Home Assistant 

![Version](https://img.shields.io/badge/version-1.2.7-blue.svg)
![Platform](https://img.shields.io/badge/platform-Home_Assistant-blue.svg)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A modern, UI-configurable integration that brings your **Class Charts** school timetable and homework tracking directly into Home Assistant. 

---

## 🛠 Features
- 👨‍🏫**Multi Pupil Support**:Upon setup, the integration creates separate sensors for each child.
- 📅**Timetable Calendar**: See lessons, teachers, and room numbers.
- 📅**Homework Calendar**: Track assignments and due dates.
- 🎭 **Behaviour Tracking**:  Keep track of student conduct.
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

## ⚙️ Options

This integration supports a dynamic **Options Flow**. You can adjust how the integration behaves at any time:
1. Navigate to **Settings** > **Devices & Services**.
2. Find **Class Charts** and click **Configure**.

### Available Settings

| Option | Default | Description |
| :--- | :--- | :--- |
| **Refresh Interval** | `24` | How often (in hours) the integration updates data from Class Charts. |
| **Days to Fetch** | `14` | How many days into the future to look for events/homework. |
| **Show Completed Homework** | `True` | Toggle to show/hide homework assignments marked as "Completed" in Class Charts. |
| **Show "No School** | `True` | Toggle to inject placeholder events on empty weekend days and holiday slots. |
| **Behaviour Tracking | Keep track of student conduct |
---
## 🗓️ Calendars

### Class Charts Timetable
A daily view of school lessons. 
- **Summary**: Subject Name
- **Location**: Room Number
- **Description**: Teacher Name

### Class Charts Homework
A view of all homework assignments.
- **Summary**: Subject and Assignment title.
- **Description**: Full task description (HTML formatting removed for readability).
- **Filtering**: Use the Configuration menu to hide completed tasks to keep your "To-Do" list clear.
---

🎭 Behaviour Tracking
- Keep track of student conduct, achievements, and recent awards directly in your dashboard.Behaviour Balance: A net score sensor (Positive points minus Negative points).Total Points: A cumulative sensor for all positive points earned.Recent Activity Feed: Detailed logs of recent behaviour events, including the reason, the teacher involved, and the timestamp.Top Achievements: Automatically identifies and lists the most frequent reasons for positive awards.

## 📊 Available Entities

### 🗓️ Calendars
| Entity ID | Description |
| :--- | :--- |
| `calendar.class_charts_"pupils Name"_timetable` | Your daily school timetable (Lessons, Rooms, Teachers). |
| `calendar.class_charts_"pupils Name"_homework` | Due dates for all assignments as calendar events. |

### 📝 Homework Sensors
| Entity ID | Description |
| :--- | :--- |
| `sensor.class_charts_"pupils Name"_outstanding_homework` | Count of active homework. Includes a list in attributes. |
| `sensor.class_charts_"pupils Name"_homework_due` | Count of homework tasks due this week. |
| `sensor.class_charts_"pupils Name"_completed_homework` | Total number of tasks marked as completed. |

### 👨‍🏫 Lesson Monitoring
| Entity ID | Description |
| :--- | :--- |
| `sensor.class_charts_"pupils Name"_current_lesson` | The subject you should be in right now. |
| `sensor.class_charts_"pupils Name"_next_lesson` | The subject coming up next. |

---

 ![Screenshot](https://github.com/skid88/Classcharts/blob/main/Timetable.png)
 ![Screenshot](https://github.com/skid88/Classcharts/blob/main/homework.png)
---
## 🎨 Dashboard: Homework List
Use a **Markdown Card** to display your assignments beautifully:

```jinja2
## 📝 Outstanding Homework
{% set items = state_attr('sensor.class_charts_"pupils Name"_outstanding_homework', 'homework_list') %}
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
## ⚖️ Disclaimer

**This is a personal, open-source project and is completely unofficial.** This integration is independently developed and maintained. It is **not** endorsed, supported, affiliated, or associated with **Class Charts** or its parent company, **Edukey Education Ltd** / **Tes Global**. 

- **Use at your own risk:** This software is provided "as is" without any guarantees or warranties. 
- **No official support:** Please do not contact Class Charts technical support regarding issues with this Home Assistant integration. If you find a bug or want to request a feature, please open an issue directly in this GitHub repository.
- **Trademarks:** All product names, logos, and brands are property of their respective owners.
---
## 🤝 Support
If you encounter any issues or have feature requests, please open an [Issue](https://github.com/skid88/Classcharts/issues) on this repository.

---

## 📝 License
This project is for personal use and is not an official Class Charts product.

