# core/notifications/templates.py
"""
Jinja2 message templates for all notification event types.
Keep all message content here — never hardcode in business logic.
"""
from jinja2 import Environment, BaseLoader

jinja_env = Environment(loader=BaseLoader())

TEMPLATES: dict[str, dict[str, str]] = {
    "timetable_published": {
        "whatsapp": (
            "🎓 *Timetable Published — {{ semester }} Semester*\n\n"
            "Dear {{ faculty_name }},\n\n"
            "Your timetable for {{ academic_year }} is now live.\n"
            "📊 You have *{{ weekly_hours }} hrs/week* across *{{ subject_count }} subjects*.\n\n"
            "🔗 View: {{ timetable_url }}"
        ),
        "email_subject": "Timetable Published — {{ semester }} Semester {{ academic_year }}",
        "email_html": (
            "<h2>Your Timetable is Live</h2>"
            "<p>Dear {{ faculty_name }},</p>"
            "<p>Your timetable for <strong>{{ semester }} Semester, {{ academic_year }}</strong> "
            "has been published.</p>"
            "<p>Weekly load: <strong>{{ weekly_hours }} hours</strong> across {{ subject_count }} subjects.</p>"
            "<p><a href='{{ timetable_url }}'>View Your Timetable</a></p>"
        ),
    },
    "substitution_request": {
        "whatsapp": (
            "🔔 *Substitution Request*\n\n"
            "Dear {{ candidate_name }},\n\n"
            "*{{ absent_faculty }}* is unavailable for:\n"
            "📅 {{ date }} | Period {{ period }} | {{ subject_name }}\n"
            "🏫 Room: {{ room_name }}\n\n"
            "You are the best-matched substitute based on your expertise in {{ expertise }}.\n\n"
            "✅ Reply *YES* to accept\n"
            "❌ Reply *NO* to decline\n\n"
            "⏰ Please respond within 10 minutes."
        ),
        "email_subject": "Substitution Request — {{ date }} Period {{ period }}",
        "email_html": (
            "<h2>Substitution Request</h2>"
            "<p>Dear {{ candidate_name }},</p>"
            "<p>You have been identified as the best-matched substitute for "
            "<strong>{{ subject_name }}</strong> on <strong>{{ date }}</strong>, "
            "Period {{ period }} in {{ room_name }}.</p>"
            "<p>Please <a href='{{ accept_url }}'>Accept</a> or "
            "<a href='{{ reject_url }}'>Decline</a> within 10 minutes.</p>"
        ),
    },
    "substitution_confirmed": {
        "whatsapp": (
            "✅ *Substitution Confirmed*\n\n"
            "{{ subject_name }} | {{ date }} | Period {{ period }}\n"
            "🏫 Room: {{ room_name }}\n"
            "👤 Substitute: *{{ substitute_name }}*\n\n"
            "All students have been notified."
        ),
        "email_subject": "Substitution Confirmed — {{ date }} Period {{ period }}",
        "email_html": (
            "<h2>Substitution Confirmed</h2>"
            "<p><strong>{{ substitute_name }}</strong> will teach "
            "<strong>{{ subject_name }}</strong> on {{ date }}, "
            "Period {{ period }} in {{ room_name }}.</p>"
        ),
    },
    "substitution_exhausted": {
        "whatsapp": (
            "⚠️ *Substitution Unresolved*\n\n"
            "No substitute could be found for:\n"
            "📅 {{ date }} | Period {{ period }} | {{ subject_name }}\n\n"
            "Manual intervention required by department admin."
        ),
        "email_subject": "⚠️ Substitution Unresolved — {{ date }} Period {{ period }}",
        "email_html": (
            "<h2>⚠️ Substitution Unresolved</h2>"
            "<p>All substitution candidates have been exhausted for "
            "<strong>{{ subject_name }}</strong> on {{ date }}, Period {{ period }}.</p>"
            "<p>Manual intervention is required.</p>"
        ),
    },
    "clash_detected": {
        "whatsapp": (
            "⚠️ *Scheduling Clash Detected*\n\n"
            "A conflict was found in your Semester {{ semester }} draft:\n\n"
            "{{ conflict_description }}\n\n"
            "🔗 Fix now: {{ fix_url }}"
        ),
        "email_subject": "⚠️ Scheduling Clash Detected — Semester {{ semester }}",
        "email_html": (
            "<h2>⚠️ Clash Detected</h2>"
            "<p>A conflict was found in your Semester {{ semester }} draft:</p>"
            "<blockquote>{{ conflict_description }}</blockquote>"
            "<p><a href='{{ fix_url }}'>Fix Now</a></p>"
        ),
    },
    "load_warning": {
        "email_subject": "Faculty Load Warning — {{ faculty_name }}",
        "email_html": (
            "<h2>Load Warning</h2>"
            "<p>Prof. <strong>{{ faculty_name }}</strong> is at "
            "<strong>{{ load_pct }}%</strong> of their maximum weekly load "
            "({{ current_load }}/{{ max_load }} hours). "
            "Adding more subjects may exceed their cap.</p>"
        ),
    },
}


def render_template(template_id: str, channel: str, **kwargs) -> str:
    """
    Render a notification template with the given variables.

    Args:
        template_id: Key in TEMPLATES dict (e.g. "substitution_request")
        channel: "whatsapp", "email_subject", or "email_html"
        **kwargs: Template variables

    Returns:
        Rendered string
    """
    template_group = TEMPLATES.get(template_id)
    if not template_group:
        return f"[Unknown template: {template_id}]"

    template_str = template_group.get(channel)
    if not template_str:
        return f"[Unknown channel: {channel} for template: {template_id}]"

    template = jinja_env.from_string(template_str)
    return template.render(**kwargs)
