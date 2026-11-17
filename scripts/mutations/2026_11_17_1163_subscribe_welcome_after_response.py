"""#1163 -- /subscribe must not take longer for a new address than an existing one.
Each row re-breaks one half of the fix: the welcome going back inline, the Telegram
alert moving onto a worker thread (where notify() silently skips it), and the failed
welcome losing its log line."""

_S = "src/astro_ai/routes/subscribe.py"

MUTATIONS = [
    ("#1163: the welcome email is sent inside the request again (new address slower than an existing one)",
     _S,
     "        background_tasks.add_task(_send_welcome_after_response, email, lang, city, rashi)",
     "        _send_welcome_after_response(email, lang, city, rashi)",
     "test_the_welcome_email_is_sent_after_the_response_not_inside_it"),
    ("#1163: notify.subscribed runs as a background task on a worker thread (no loop, alert silently dropped)",
     _S,
     '        notify.subscribed(email=email, source=(city or "unknown"), lang=lang)',
     '        background_tasks.add_task(notify.subscribed, email=email, source=(city or "unknown"), lang=lang)',
     "test_the_telegram_alert_is_raised_on_the_event_loop_not_a_worker_thread"),
    ("#1163: a failed post-response welcome is swallowed without a log line",
     _S,
     '        logging.getLogger(__name__).warning("welcome email failed for %s: %s", email, err)',
     "        pass",
     "test_a_failed_welcome_is_logged_and_does_not_break_the_response"),
]
