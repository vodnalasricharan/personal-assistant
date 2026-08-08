# Personal Knowledge Base

This directory contains all the documents that power your Personal AI Assistant's knowledge base.

## How to add your information

1. Create or copy your files into this directory (and subdirectories if you like).
2. Go to the **Knowledge Base** page in Streamlit → click **Run bulk ingest**, or
3. Upload individual files directly from the Knowledge Base page.

## Supported formats

| Extension | Notes |
|-----------|-------|
| `.pdf`    | Resume, certificates, papers |
| `.docx`   | Word documents |
| `.txt`    | Plain text notes |
| `.md` / `.markdown` | Markdown files (recommended) |
| `.json`   | Structured data |
| `.csv`    | Tabular data (skills, timeline) |

## Recommended file structure

```
data/
├── about_me.md          ← Brief personal summary
├── resume.pdf           ← Your resume / CV
├── experience.md        ← Detailed work history
├── education.md         ← Academic background
├── skills.md            ← Technical and soft skills
├── achievements.md      ← Awards, accomplishments
├── certifications.md    ← Professional certifications
├── publications.md      ← Papers, articles, talks
├── faq.md               ← Frequently asked questions
└── projects/
    ├── project1.md
    ├── project2.md
    └── project3.md
```

## Tips

- Use descriptive filenames — they are used to infer document type automatically.
  - Files with `resume` or `cv` in the name → treated as resume
  - Files with `experience` → work history
  - Files with `project` → projects
  - etc.

- The more detail you add, the better the assistant can answer questions.

- Re-running bulk ingest is safe — existing entries are updated (upsert).

- **Never include sensitive data** (passwords, private keys, etc.) in this directory.
