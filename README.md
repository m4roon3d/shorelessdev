# shoreless.dev

Remote data roles open to India, fresh from the source.

A personal job feed for remote data engineering, analytics and architect roles that are open to candidates in India.

It pulls listings directly from company hiring systems (Greenhouse, Lever, Ashby, SmartRecruiters, Workable) plus free remote feeds (Hacker News "Who's Hiring", Remotive, RemoteOK, Himalayas, Jobicy, We Work Remotely). Closed roles disappear on the next refresh, so nothing goes stale.

## What it does
- **Today:** the 15 best-fitting open roles as a deck. Pass, save or mark applied; when it's empty you're done.
- **Browse:** every role, filterable by who can apply, role, stack, direct apply and age.
- **Pipeline:** saved and applied jobs by stage, with notes, follow-up nudges and a flag when a posting closes.
- **Pulse:** stack demand, who's hiring, freshness and which skill would open the most roles.
- Roles are tagged by who can apply (India remote, India office, APAC, Worldwide, Unclear, Region-locked) and by the stack named in the description.
- Refreshes every 6 hours. Your stack, saves and pipeline stay in your browser.

## Add or fix companies
Edit `companies.py`. The slug is the part of the company's job board URL:
- `boards.greenhouse.io/<slug>`
- `jobs.lever.co/<slug>`
- `jobs.ashbyhq.com/<slug>`
- `jobs.smartrecruiters.com/<slug>`
- `apply.workable.com/<slug>`

Push the change and Render redeploys automatically.

## Run locally
```
pip install -r requirements.txt
python app.py   # http://localhost:8000
```

RemoteOK listings are shown with credit to [RemoteOK](https://remoteok.com). Remotive listings link back to [Remotive](https://remotive.com).
