
novel-mail-bot
==============

How to deploy to Render:
1. Upload this project to a GitHub repo and connect to Render (or upload files directly to Render).
2. Add environment variables in Render (Service -> Environment):
   - EMAIL_ACCOUNT : your Gmail address (e.g. yourbot@gmail.com)
   - EMAIL_PASSWORD: your Gmail app password (16 chars)
   - CHECK_INTERVAL: optional, seconds (default 25)
3. Start command: python bot.py
4. Send an email to EMAIL_ACCOUNT with the novel directory URL in subject or body.
   The bot will reply to the sender with the generated TXT attached.

Notes:
- Use Gmail IMAP and SMTP with app password (enable 2-step verification and create app password).
- Do NOT commit real passwords to a public repo; use Render environment variables.
- The crawler is simple; for very large books consider increasing timeouts or decreasing concurrency.
