# 0010 One form session shared by wizard and chat
**Context:** The cockpit has a form wizard; Lotsi can also fill forms. Two parallel drafts would diverge and lose answers.

**Decision:** One schema and one `form_sessions` record per draft. `next-questions` returns only what is missing (both clients ask the same). `ChatRequest.form_session_id` makes Lotsi continue exactly the session open in the wizard (which polls every 2 s); `start_form` is idempotent per conversation. Choice values are normalised to the official options; validation errors (422) are relayed verbatim.

**Consequence:** "Trag ein, dass wir die Pflegeberatung möchten" changes the open wizard within seconds; the person can switch between clicking and chatting at any time.
