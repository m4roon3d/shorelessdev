# shoreless.dev

Remote data roles open to India, fresh from the source.

A personal job feed for remote data engineering, analytics and architect roles that are open to candidates in India.

It pulls listings directly from company hiring systems (Greenhouse, Lever, Ashby, SmartRecruiters, Workable) plus free remote feeds (Hacker News "Who's Hiring", Remotive, RemoteOK, Himalayas, Jobicy, We Work Remotely). Closed roles disappear on the next refresh, so nothing goes stale.

## What it does
- Keeps only data roles: Engineering, Analytics, Architecture, Science.
- Tags each job by who can apply: India, APAC, Worldwide, Unclear, or Region-locked (hidden by default).
- Flags supply chain / logistics roles.
- Marks jobs that are new since your last visit; Save and Mark applied are kept in your browser.
- Refreshes every 6 hours. The Sources panel shows which boards are working.

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
