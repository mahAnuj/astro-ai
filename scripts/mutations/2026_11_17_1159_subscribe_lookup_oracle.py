"""#1159 -- /subscribe/lookup was an email-enumeration oracle. Each row re-opens one half
of the fix: the identity gate, the order of gate and storage read, the ownership test, or
the /subscribe overwrite gate that replaced the prefill's job."""

_R = "src/astro_ai/routes/subscribe.py"
_GATE = ("    if not _is_signed_in_as(request, email):\n"
         "        return JSONResponse(dict(_LOOKUP_NO_ANSWER))\n")
_OWNER = "    return bool(email.strip()) and user.email.strip().lower() == email.strip().lower()\n"

MUTATIONS = [
    ("#1159: lookup answers anonymous callers again (subscribed vs unsubscribed differ, city/rashi leak)",
     _R,
     _GATE + "    sub = subscribers.find_by_email(email)\n",
     "    sub = subscribers.find_by_email(email)\n",
     "test_anonymous_lookup_returns_one_body_for_subscribed_and_unsubscribed"),
    ("#1159: lookup reads the subscriber list before checking who is asking (timing oracle)",
     _R,
     _GATE + "    sub = subscribers.find_by_email(email)\n",
     "    sub = subscribers.find_by_email(email)\n" + _GATE,
     "test_anonymous_lookup_never_reads_the_subscriber_list"),
    ("#1159: any signed-in user passes the ownership test (user A reads user B's prefs)",
     _R,
     _OWNER,
     "    return True\n",
     "test_signed_in_user_cannot_look_up_someone_elses_address"),
    ("#1159: ownership compares case-sensitively (the modal's lower-cased email stops matching)",
     _R,
     _OWNER,
     "    return bool(email.strip()) and user.email.strip() == email.strip()\n",
     "test_signed_in_user_gets_their_own_prefs_back"),
    ("#1159: /subscribe overwrites an existing address's prefs for anonymous callers",
     _R,
     "            overwrite_prefs=_is_signed_in_as(request, email))\n",
     "            overwrite_prefs=True)\n",
     "test_anonymous_resubscribe_keeps_the_stored_prefs_and_looks_like_a_new_signup"),
    ("#1159: /subscribe never overwrites, so the signed-in 'Edit preferences' flow stops saving",
     _R,
     "            overwrite_prefs=_is_signed_in_as(request, email))\n",
     "            overwrite_prefs=False)\n",
     "test_signed_in_resubscribe_of_their_own_address_updates_the_prefs"),
    ("#1159: subscribe() ignores overwrite_prefs=False (the stored record is rewritten anyway)",
     "src/astro_ai/subscribers.py",
     "                if overwrite_prefs:\n",
     "                if True:\n",
     "test_subscribe_overwrite_default_is_unchanged_for_other_callers"),
]
