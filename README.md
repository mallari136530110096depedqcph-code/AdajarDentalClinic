# ADAJAR Dental Appointment System (Flask)

A Flask + SQLite version of the ADAJAR Online Dental Appointment website.

## Features
- Home and About pages based on the original project
- Account registration and login
- Password hashing using Werkzeug
- Unique email validation to prevent duplicate accounts
- Appointment booking with date, time slot, and dental procedure
- SQLite persistence (appointments remain after logout/restart)
- Live availability endpoint
- Personal appointment schedule and cancellation
- Responsive layout for desktop, tablet, and mobile

## Run locally (Windows)

```powershell
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Deploy on PythonAnywhere

1. Upload this project folder or its ZIP to your PythonAnywhere account.
2. Open a Bash console and go to the project directory:
   `cd ~/adajar_dental_flask`
3. Create and activate a virtual environment:
   `python3.11 -m venv venv`
   `source venv/bin/activate`
4. Install dependencies:
   `pip install -r requirements.txt`
5. Open the **Web** tab and create a new **Manual configuration** web app using Python 3.11.
6. Set the source code directory to `/home/YOUR_USERNAME/adajar_dental_flask`.
7. Set the virtualenv path to `/home/YOUR_USERNAME/adajar_dental_flask/venv`.
8. Open the WSGI configuration file and replace its contents with:

```python
import sys
project_home = '/home/YOUR_USERNAME/adajar_dental_flask'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application
```

Replace `YOUR_USERNAME` with your actual PythonAnywhere username.
9. Save the WSGI file and click **Reload** on the Web tab.

The SQLite database is created automatically in the project folder. Keep the project folder in your PythonAnywhere home directory so the database can be written there.

## Before public deployment

- Change `SECRET_KEY` to a long random value. In the WSGI file, set it before importing the app:
  `os.environ['SECRET_KEY'] = 'your-long-random-secret'`
- Use HTTPS (PythonAnywhere provides HTTPS for hosted domains).
- Back up `adajar_dental.db` regularly.
- Do not share your database or secret key.
- This is a patient booking prototype, not a substitute for a clinic's verified scheduling and privacy procedures.

## Important notes
- The clinic is configured as closed on Sundays.
- The four default time slots are 08:00–10:00, 10:00–12:00, 13:00–15:00, and 15:00–17:00. Change `TIME_SLOTS` in `app.py` if the clinic uses different hours.
- The app prevents two bookings from taking the same date and time slot.
