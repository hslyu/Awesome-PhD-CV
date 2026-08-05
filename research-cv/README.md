# Data-driven academic CV

`cv.tex` keeps the Awesome-CV presentation. Its content is generated from:

- `portfolio.yml` in the parent portfolio repository: profile, experience, education, awards, services, projects, domestic papers, and intellectual properties;
- `papers.bib` in the parent portfolio repository: all international publications;
- `cv-extra.yml` here: only CV-specific prose and optional extra sections.

Do not copy portfolio records into this repository. Add website-visible structured content to the parent repository, add publications to its BibTeX file, and reserve `cv-extra.yml` for information that belongs only in the CV.

From the parent repository, generate the TeX fragments with:

```bash
python vendor/awesome-phd-cv/research-cv/scripts/render_cv.py \
  --portfolio content/portfolio.yml \
  --bibliography _bibliography/papers.bib \
  --extra vendor/awesome-phd-cv/research-cv/cv-extra.yml \
  --output vendor/awesome-phd-cv/research-cv/generated
```

Then compile from `research-cv/` with XeLaTeX:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error cv.tex
```

The parent portfolio workflow performs both steps and copies the resulting PDF into its Jekyll build artifact.
