# Data Privacy Notes

The local project contains private user profile material copied from `<private-profile-source>\profiles\豆瓣酱`.

These files may include phone number, email address, resume documents, PDF/DOCX artifacts, fine-tuning data, and interview preparation notes. They are useful for local development but should not be committed to a public GitHub repository.

Current policy:

- `data/profiles/*` is ignored by Git.
- `data/profiles/.gitkeep` is tracked to preserve the directory.
- Demo-safe sample profiles should be added separately before public demos.
- Backend code must mask phone, email, and precise location in public demo mode.

