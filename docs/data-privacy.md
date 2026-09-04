# Data Privacy Notes

The local project contains private source material copied from `<private-profile-source>\profiles\豆瓣酱`.

These files may include phone number, email address, resume documents, PDF/DOCX artifacts, fine-tuning data, and interview preparation notes. They are useful for local development but should not be committed to a public GitHub repository.

Current policy:

- `data/profiles/*` is the resume-optimization and fine-tuning source database. It is ignored by Git and is not the interview runtime resume.
- `data/profiles/.gitkeep` is tracked to preserve the directory.
- `data/interview_profiles/*` contains only interview-specific profile snapshots and is ignored by Git.
- `data/interview_job_descriptions/*` contains only interview-specific JD snapshots and is ignored by Git.
- The backend reads only the two interview-specific directories through `ProfileLoader`.
- Demo-safe sample profiles should be added separately before public demos.
- Backend code must mask phone, email, and precise location in public demo mode.
