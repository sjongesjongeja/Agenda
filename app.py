import os
import sqlite3
import calendar
import secrets
from datetime import datetime, date, time, timedelta
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    session,
    jsonify,
    g
)

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'agenda-secret-key-change-in-production-2026')
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agenda.db')

# Dutch locale text mappings
DUTCH_MONTHS = [
    "", "Januari", "Februari", "Maart", "April", "Mei", "Juni",
    "Juli", "Augustus", "September", "Oktober", "November", "December"
]

DUTCH_DAYS = [
    "Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"
]

DUTCH_DAYS_SHORT = ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"]

# Default preset colors
PRESET_COLORS = [
    {"label": "Mintgroen", "value": "#2DD4A8"},
    {"label": "Oceaanblauw", "value": "#3B82F6"},
    {"label": "Zonsondergang", "value": "#F59E0B"},
    {"label": "Koraalrood", "value": "#EF4444"},
    {"label": "Paars", "value": "#8B5CF6"},
    {"label": "Roze", "value": "#EC4899"}
]


# ============================================================================
# Database Connection & Initialization
# ============================================================================

def get_db():
    """Get a database connection, reusing per request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        # Enable foreign keys and busy timeout
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA busy_timeout = 3000")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """Close the database connection when request context tears down."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Ensure database schema is created and migrated on startup."""
    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                event_date TEXT NOT NULL,
                end_date TEXT,
                start_time TEXT,
                end_time TEXT,
                location TEXT,
                color TEXT DEFAULT '#2DD4A8',
                created_at TEXT NOT NULL
            );
        """)
        # Migration: ensure end_date column exists in existing database
        cursor = conn.execute("PRAGMA table_info(events)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        if 'end_date' not in existing_cols:
            conn.execute("ALTER TABLE events ADD COLUMN end_date TEXT;")
        conn.commit()
    finally:
        conn.close()


# Ensure DB exists immediately
init_db()


# ============================================================================
# CSRF Protection & Context Processors
# ============================================================================

@app.before_request
def csrf_protect():
    """Simple, zero-dependency CSRF token verification."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)

    if request.method == 'POST':
        token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
        if not token or token != session.get('_csrf_token'):
            abort(400, description="Ongeldig of ontbrekend CSRF-beveiligingstoken.")


@app.context_processor
def inject_globals():
    """Make common variables and helpers available in all templates."""
    def csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(24)
        return session['_csrf_token']

    return {
        'csrf_token': csrf_token,
        'today_date': date.today(),
        'preset_colors': PRESET_COLORS,
        'dutch_days_short': DUTCH_DAYS_SHORT
    }


# ============================================================================
# Template Filters
# ============================================================================

@app.template_filter('dutch_date')
def dutch_date_filter(val):
    """Format YYYY-MM-DD or date object to 'Woensdag 10 september 2026'."""
    if not val:
        return ""
    if isinstance(val, str):
        try:
            d = datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            return val
    elif isinstance(val, (datetime, date)):
        d = val if isinstance(val, date) else val.date()
    else:
        return str(val)

    weekday_name = DUTCH_DAYS[d.weekday()]
    month_name = DUTCH_MONTHS[d.month].lower()
    return f"{weekday_name} {d.day} {month_name} {d.year}"


@app.template_filter('dutch_date_short')
def dutch_date_short_filter(val):
    """Format YYYY-MM-DD or date object to '10 sep 2026'."""
    if not val:
        return ""
    if isinstance(val, str):
        try:
            d = datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            return val
    elif isinstance(val, (datetime, date)):
        d = val if isinstance(val, date) else val.date()
    else:
        return str(val)

    month_name = DUTCH_MONTHS[d.month][:3].lower()
    return f"{d.day} {month_name} {d.year}"


@app.template_filter('event_date_display')
def event_date_display(ev):
    """Format single day or multi-day range nicely in Dutch."""
    if not ev:
        return ""
    start_d = ev['event_date'] if isinstance(ev, (dict, sqlite3.Row)) else getattr(ev, 'event_date', '')
    end_d = ev['end_date'] if isinstance(ev, (dict, sqlite3.Row)) else getattr(ev, 'end_date', None)
    
    if not end_d or end_d == start_d:
        return dutch_date_short_filter(start_d)
    return f"{dutch_date_short_filter(start_d)} t/m {dutch_date_short_filter(end_d)}"


@app.template_filter('event_date_full_range')
def event_date_full_range(ev):
    """Full Dutch date description for detail views."""
    if not ev:
        return ""
    start_d = ev['event_date'] if isinstance(ev, (dict, sqlite3.Row)) else getattr(ev, 'event_date', '')
    end_d = ev['end_date'] if isinstance(ev, (dict, sqlite3.Row)) else getattr(ev, 'end_date', None)

    if not end_d or end_d == start_d:
        return dutch_date_filter(start_d)
    return f"{dutch_date_filter(start_d)} t/m {dutch_date_filter(end_d)}"


# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    """Main calendar overview page with multi-day support."""
    today = date.today()

    # Parse year and month query parameters, default to current month
    try:
        year = int(request.args.get('year', today.year))
    except (ValueError, TypeError):
        year = today.year

    try:
        month = int(request.args.get('month', today.month))
    except (ValueError, TypeError):
        month = today.month

    # Boundary check for month
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    # Selected day query param, defaults to today if same month/year, else day 1
    try:
        selected_day = int(request.args.get('day', today.day if (year == today.year and month == today.month) else 1))
    except (ValueError, TypeError):
        selected_day = 1

    # Clamp selected day to number of days in the month
    max_days = calendar.monthrange(year, month)[1]
    if selected_day < 1:
        selected_day = 1
    elif selected_day > max_days:
        selected_day = max_days

    selected_date = date(year, month, selected_day)

    # Calculate previous and next month URLs
    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1

    if month == 12:
        next_year = year + 1
        next_month = 1
    else:
        next_year = year
        next_month = month + 1

    # Build calendar grid using Python's calendar (starts on Monday = 0)
    cal = calendar.Calendar(firstweekday=0)
    month_matrix = cal.monthdatescalendar(year, month)

    # Calculate range for fetching events (including spanning multi-day events)
    min_date_str = month_matrix[0][0].strftime('%Y-%m-%d')
    max_date_str = month_matrix[-1][-1].strftime('%Y-%m-%d')

    db = get_db()
    cursor = db.execute(
        """
        SELECT * FROM events
        WHERE event_date <= ? AND COALESCE(NULLIF(end_date, ''), event_date) >= ?
        ORDER BY event_date ASC, COALESCE(start_time, '') ASC
        """,
        (max_date_str, min_date_str)
    )
    all_events = cursor.fetchall()

    # Group events by each date they span
    events_by_date = {}
    for ev in all_events:
        ev_dict = dict(ev)
        s_date = datetime.strptime(ev_dict['event_date'], "%Y-%m-%d").date()
        e_date_str = ev_dict['end_date'] or ev_dict['event_date']
        e_date = datetime.strptime(e_date_str, "%Y-%m-%d").date()
        
        is_multiday = (e_date > s_date)
        ev_dict['is_multiday'] = is_multiday

        curr_d = s_date
        step = timedelta(days=1)
        while curr_d <= e_date:
            curr_str = curr_d.strftime('%Y-%m-%d')
            if curr_str not in events_by_date:
                events_by_date[curr_str] = []
            
            day_instance = dict(ev_dict)
            day_instance['is_first_day'] = (curr_d == s_date)
            day_instance['is_last_day'] = (curr_d == e_date)
            events_by_date[curr_str].append(day_instance)
            curr_d += step

    # Construct calendar weeks data
    calendar_weeks = []
    for week in month_matrix:
        week_days = []
        for d in week:
            d_str = d.strftime('%Y-%m-%d')
            week_days.append({
                'date': d,
                'date_str': d_str,
                'day_number': d.day,
                'is_current_month': (d.month == month),
                'is_today': (d == today),
                'is_selected': (d == selected_date),
                'events': events_by_date.get(d_str, [])
            })
        calendar_weeks.append(week_days)

    # Events for currently selected date
    selected_date_str = selected_date.strftime('%Y-%m-%d')
    selected_day_events = events_by_date.get(selected_date_str, [])

    return render_template(
        'index.html',
        year=year,
        month=month,
        month_name=DUTCH_MONTHS[month],
        selected_date=selected_date,
        selected_date_str=selected_date_str,
        selected_day_events=selected_day_events,
        calendar_weeks=calendar_weeks,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        today=today
    )


@app.route('/add', methods=['GET', 'POST'])
def add_event():
    """Add a new calendar appointment (supports single and multi-day)."""
    today = date.today()
    default_date = request.args.get('date', today.strftime('%Y-%m-%d'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        event_date = request.form.get('event_date', '').strip()
        end_date = request.form.get('end_date', '').strip() or None
        start_time = request.form.get('start_time', '').strip() or ''
        end_time = request.form.get('end_time', '').strip() or None
        description = request.form.get('description', '').strip() or None
        location = request.form.get('location', '').strip() or None
        color = request.form.get('color', '#2DD4A8').strip() or '#2DD4A8'

        errors = []

        if not title:
            errors.append("Titel is verplicht.")

        parsed_start_date = None
        if not event_date:
            errors.append("Datum (of startdatum) is verplicht.")
        else:
            try:
                parsed_start_date = datetime.strptime(event_date, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Ongeldige datumindeling. Gebruik JJJJ-MM-DD.")

        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                if parsed_start_date and parsed_end_date < parsed_start_date:
                    errors.append("Einddatum mag niet vóór de startdatum liggen.")
            except ValueError:
                errors.append("Ongeldige einddatum. Gebruik JJJJ-MM-DD.")

        if start_time:
            try:
                datetime.strptime(start_time, "%H:%M")
            except ValueError:
                errors.append("Ongeldige begintijd. Gebruik UU:MM.")

        if end_time:
            try:
                t_end = datetime.strptime(end_time, "%H:%M").time()
                # If single-day event and start_time is set, check end_time >= start_time
                if (not end_date or end_date == event_date) and start_time:
                    t_start = datetime.strptime(start_time, "%H:%M").time()
                    if t_end < t_start:
                        errors.append("Eindtijd mag niet vóór de begintijd liggen op dezelfde dag.")
            except ValueError:
                errors.append("Ongeldige eindtijd. Gebruik UU:MM.")

        if errors:
            for err in errors:
                flash(err, 'error')
            return render_template(
                'add.html',
                form_data=request.form,
                default_date=event_date or default_date
            )

        # Insert into SQLite database
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO events (title, description, event_date, end_date, start_time, end_time, location, color, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, description, event_date, end_date, start_time, end_time, location, color, now_str)
        )
        db.commit()

        flash(f"Afspraak '{title}' is succesvol toegevoegd!", 'success')

        p_date = datetime.strptime(event_date, "%Y-%m-%d").date()
        return redirect(url_for('index', year=p_date.year, month=p_date.month, day=p_date.day))

    return render_template('add.html', default_date=default_date, form_data={})


@app.route('/event/<int:event_id>')
def view_event(event_id):
    """View appointment details."""
    db = get_db()
    cursor = db.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()

    if not event:
        abort(404, description=f"Afspraak met ID {event_id} is niet gevonden.")

    # Return JSON if requested by modal AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('format') == 'json':
        ev_dict = dict(event)
        ev_dict['formatted_date'] = event_date_full_range(ev_dict)
        return jsonify(ev_dict)

    return render_template('event.html', event=event)


@app.route('/edit/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    """Edit an existing appointment."""
    db = get_db()
    cursor = db.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()

    if not event:
        abort(404, description=f"Afspraak met ID {event_id} is niet gevonden.")

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        event_date = request.form.get('event_date', '').strip()
        end_date = request.form.get('end_date', '').strip() or None
        start_time = request.form.get('start_time', '').strip() or ''
        end_time = request.form.get('end_time', '').strip() or None
        description = request.form.get('description', '').strip() or None
        location = request.form.get('location', '').strip() or None
        color = request.form.get('color', '#2DD4A8').strip() or '#2DD4A8'

        errors = []

        if not title:
            errors.append("Titel is verplicht.")

        parsed_start_date = None
        if not event_date:
            errors.append("Datum (of startdatum) is verplicht.")
        else:
            try:
                parsed_start_date = datetime.strptime(event_date, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Ongeldige datumindeling. Gebruik JJJJ-MM-DD.")

        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                if parsed_start_date and parsed_end_date < parsed_start_date:
                    errors.append("Einddatum mag niet vóór de startdatum liggen.")
            except ValueError:
                errors.append("Ongeldige einddatum. Gebruik JJJJ-MM-DD.")

        if start_time:
            try:
                datetime.strptime(start_time, "%H:%M")
            except ValueError:
                errors.append("Ongeldige begintijd. Gebruik UU:MM.")

        if end_time:
            try:
                t_end = datetime.strptime(end_time, "%H:%M").time()
                if (not end_date or end_date == event_date) and start_time:
                    t_start = datetime.strptime(start_time, "%H:%M").time()
                    if t_end < t_start:
                        errors.append("Eindtijd mag niet vóór de begintijd liggen op dezelfde dag.")
            except ValueError:
                errors.append("Ongeldige eindtijd. Gebruik UU:MM.")

        if errors:
            for err in errors:
                flash(err, 'error')
            return render_template('edit.html', event=dict(request.form, id=event_id))

        # Update event
        db.execute(
            """
            UPDATE events
            SET title = ?, description = ?, event_date = ?, end_date = ?, start_time = ?, end_time = ?, location = ?, color = ?
            WHERE id = ?
            """,
            (title, description, event_date, end_date, start_time, end_time, location, color, event_id)
        )
        db.commit()

        flash("Afspraak is succesvol bijgewerkt!", 'success')
        p_date = datetime.strptime(event_date, "%Y-%m-%d").date()
        return redirect(url_for('index', year=p_date.year, month=p_date.month, day=p_date.day))

    return render_template('edit.html', event=event)


@app.route('/delete/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    """Delete an appointment."""
    db = get_db()
    cursor = db.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()

    if not event:
        abort(404, description=f"Afspraak met ID {event_id} is niet gevonden.")

    event_date = event['event_date']
    title = event['title']

    db.execute("DELETE FROM events WHERE id = ?", (event_id,))
    db.commit()

    flash(f"Afspraak '{title}' is verwijderd.", 'info')

    try:
        p_date = datetime.strptime(event_date, "%Y-%m-%d").date()
        return redirect(url_for('index', year=p_date.year, month=p_date.month, day=p_date.day))
    except ValueError:
        return redirect(url_for('index'))


@app.route('/search')
def search():
    """Search appointments by title, description or location."""
    query = request.args.get('q', '').strip()
    events = []

    if query:
        db = get_db()
        pattern = f"%{query}%"
        cursor = db.execute(
            """
            SELECT * FROM events
            WHERE title LIKE ? OR description LIKE ? OR location LIKE ?
            ORDER BY event_date DESC, COALESCE(start_time, '') ASC
            """,
            (pattern, pattern, pattern)
        )
        events = cursor.fetchall()

    return render_template('search.html', query=query, events=events)


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(400)
def bad_request_error(e):
    return render_template('400.html', error=e), 400


@app.errorhandler(404)
def not_found_error(e):
    return render_template('404.html', error=e), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html', error=e), 500


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
