from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime, timedelta
import random
import calendar

app = Flask(__name__)

# ===================== GLOBALS =====================
users_tasks = {}
events = []

themes = [
    "light", "dark", "blue", "red", "green", "purple",
    "orange", "pink", "gray", "black", "yellow", "cyan"
]
current_theme = "dark"

daily_quotes = [
    "Believe you can and you're halfway there.",
    "Don’t watch the clock; do what it does. Keep going.",
    "The secret of getting ahead is getting started.",
    "Focus on being productive instead of busy.",
    "Small steps every day.",
    "Success is the sum of small efforts repeated.",
    "Don’t wait for opportunity. Create it.",
    "Your limitation—it's only your imagination.",
    "Push yourself, because no one else is going to do it for you.",
    "Great things take time.",
    "Let us pick up our books and our pens. They are our most powerful weapons.",
    "Everything you can imagine is real.",
    "There is no substitute for hard work.",
    "The time is always right to do what is right",
]

pomodoro_sessions = {}

planner_notes = {}

# ===================== ROUTES =====================

@app.route('/')
def home():
    quote = random.choice(daily_quotes)
    return render_template('index.html', theme=current_theme, quote=quote, themes=themes)

@app.route('/get_note', methods=['POST'])
def get_note():
    data = request.json
    key = f"{data['year']:04d}-{data['month']:02d}-{data['day']:02d}"
    note = planner_notes.get(key, "")
    return jsonify({"note": note})

@app.route('/save_note', methods=['POST'])
def save_note():
    data = request.json
    key = f"{data['year']:04d}-{data['month']:02d}-{data['day']:02d}"
    planner_notes[key] = data.get('note', "")
    return jsonify({"success": True})

# ---------- TO-DO ----------

@app.route('/todo', methods=['GET', 'POST'])
def todo():
    user = 'default_user'
    if request.method == 'POST':
        task = request.form.get('task')
        if user not in users_tasks:
            users_tasks[user] = []
        users_tasks[user].append({'task': task, 'done': False})
        return redirect(url_for('todo'))
    tasks = users_tasks.get(user, [])
    return render_template('todo.html', tasks=tasks, theme=current_theme)

@app.route('/todo/toggle/<int:task_id>')
def toggle_task(task_id):
    user = 'default_user'
    tasks = users_tasks.get(user, [])
    if 0 <= task_id < len(tasks):
        tasks[task_id]['done'] = not tasks[task_id]['done']
    return redirect(url_for('todo'))

@app.route('/todo/delete/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    user = 'default_user'
    tasks = users_tasks.get(user, [])
    if 0 <= task_id < len(tasks):
        tasks.pop(task_id)
    return redirect(url_for('todo'))

# ---------- EVENTS ----------

@app.route('/events', methods=['GET', 'POST'])
def manage_events():
    global events
    if request.method == 'POST':
        name = request.form.get('name')
        date = request.form.get('date')
        events.append({'name': name, 'date': date})
        return redirect(url_for('manage_events'))
    return render_template('events.html', events=events, theme=current_theme)

@app.route('/events/delete/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    global events
    if 0 <= event_id < len(events):
        events.pop(event_id)
    return redirect(url_for('manage_events'))

# ---------- CALENDAR ----------

@app.route('/calendar')
def calendar_view():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    week_header = list(calendar.day_abbr)
    return render_template(
        'calendar.html',
        theme=current_theme,
        year=year,
        month=month,
        month_name=month_name,
        week_header=week_header,
        cal=cal,
        calendar=calendar
    )

# ---------- POMODORO ----------

@app.route('/pomodoro', methods=['GET', 'POST'])
def pomodoro():
    user = 'default_user'
    default_work, default_break = 25, 5

    if request.method == 'POST':
        action = request.form.get('action')
        preset = request.form.get('preset', '25-5')
        custom_work = int(request.form.get('custom_work', default_work))
        custom_break = int(request.form.get('custom_break', default_break))

        if preset == 'custom':
            work, brk = custom_work, custom_break
        elif preset == '25-10':
            work, brk = 25, 10
        elif preset == '30-0':
            work, brk = 30, 0
        else:
            work, brk = 25, 5

        if action == 'start':
            pomodoro_sessions[user] = {
                'mode': 'work',
                'work_len': work * 60,
                'break_len': brk * 60,
                'end_time': datetime.now() + timedelta(seconds=work * 60),
                'buzzer': False
            }
        elif action == 'stop':
            sess = pomodoro_sessions.get(user)
            if sess:
                sess['end_time'] = None
        elif action == 'reset':
            pomodoro_sessions.pop(user, None)
        elif action == 'ok':
            sess = pomodoro_sessions.get(user)
            if sess:
                sess['buzzer'] = False

    session = pomodoro_sessions.get(user)
    return render_template('pomodoro.html', session=session, theme=current_theme)

@app.route('/pomodoro/status')
def pomodoro_status():
    user = 'default_user'
    sess = pomodoro_sessions.get(user)
    if not sess:
        return jsonify({'running': False, 'buzzer': False})

    if sess['end_time'] is None:
        return jsonify({'running': False, 'mode': sess['mode'], 'remaining': 0, 'buzzer': sess.get('buzzer', False)})

    remaining = int((sess['end_time'] - datetime.now()).total_seconds())

    if remaining <= 0:
        if not sess.get('buzzer', False):
            sess['buzzer'] = True
            sess['buzzer_stop_time'] = datetime.now() + timedelta(seconds=60)
        if datetime.now() > sess.get('buzzer_stop_time', datetime.now()):
            sess['buzzer'] = False
        sess['end_time'] = None

    return jsonify({
        'running': sess['end_time'] is not None,
        'mode': sess['mode'],
        'remaining': max(0, remaining),
        'work_len': sess['work_len'] // 60,
        'break_len': sess['break_len'] // 60,
        'buzzer': sess.get('buzzer', False)
    })

# ---------- THEMES ----------

@app.route('/themes', methods=['POST'])
def change_theme():
    global current_theme
    theme = request.json.get('theme')
    if theme in themes:
        current_theme = theme
        return jsonify({'status': 'success', 'theme': theme})
    return jsonify({'status': 'error', 'message': 'Invalid theme'})

# ---------- EXTRA ----------

@app.route('/quote')
def get_quote():
    return jsonify({'quote': random.choice(daily_quotes)})

@app.route('/time')
def get_time():
    now = datetime.now()
    return jsonify({'time': now.strftime('%H:%M:%S'), 'date': now.strftime('%Y-%m-%d')})

# ===== MAIN =====
if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
