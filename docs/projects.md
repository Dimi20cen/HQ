# Projects
read_when: managing the private project catalog that feeds portfolio

HQ keeps a separate project registry for public publishing decisions.

Core ideas
- A project is not the same thing as a runnable HQ tool.
- HQ owns the canonical project records.
- Portfolio consumes only a sanitized export JSON file.
- Public ordering is controlled only by `sort_order`.

Stored fields
- `slug`
- `title`
- `public_summary`
- `public_mode`: `none | docs | demo | full`
- `primary_url`
- `repo_url`
- `sort_order`
- `linked_tools`

Runtime storage
- Registry file: `runtime/projects/projects.json`
- Default export target: `runtime/projects/projects.generated.json`
- Override with env:
  - `HQ_PROJECTS_PATH`
  - `HQ_PROJECTS_EXPORT_PATH`

Controller routes
- `GET /projects`
- `POST /projects`
- `PUT /projects/{slug}`
- `POST /projects/export`

Export script
```bash
python bin/export-portfolio-projects.py
```

This writes to the HQ runtime export path by default, which is safe for the
deployed container.

Optional explicit export path:
```bash
python bin/export-portfolio-projects.py /path/to/projects.generated.json
```

For local portfolio updates, pass the portfolio repo path explicitly:
```bash
python bin/export-portfolio-projects.py /home/dim/Projects/dimy.dev/data/projects.generated.json
```
