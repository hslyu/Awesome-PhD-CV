#!/usr/bin/env python3
"""Render the academic CV from portfolio YAML, BibTeX, and CV-only YAML."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import bibtexparser
import yaml
from bibtexparser.bparser import BibTexParser


SECTION_KEYS = {
    "research_profile",
    "education",
    "experience",
    "publications",
    "domestic_papers",
    "intellectual_properties",
    "awards",
    "key_projects",
    "academic_services",
    "talks",
    "additional_sections",
}


def latex(value: object) -> str:
    """Escape plain text for LaTeX without accepting raw TeX from data files."""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in str(value or ""))


def bib_text(value: object) -> str:
    """Turn BibTeX brace protection into ordinary text before LaTeX escaping."""
    cleaned = str(value or "").replace(r"\&", "&").replace("{", "").replace("}", "")
    return latex(cleaned)


def url_argument(value: object) -> str:
    return str(value or "").replace("%", r"\%").replace("#", r"\#")


def read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def read_bibliography(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
    parser = BibTexParser(common_strings=True)
    database = bibtexparser.loads(text, parser=parser)
    entries = database.entries
    identifiers = [entry.get("ID") for entry in entries]
    if not entries:
        raise ValueError(f"{path} contains no bibliography entries")
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"{path} contains duplicate bibliography keys")
    return entries


def require_mapping(data: dict, key: str, source: Path) -> dict:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{source}: '{key}' must be a mapping")
    return value


def human_name(raw_name: str) -> str:
    if "," not in raw_name:
        return " ".join(raw_name.split())
    family, given = (part.strip() for part in raw_name.split(",", 1))
    return f"{given} {family}".strip()


def author_list(raw_authors: object, separator: str = " and ") -> str:
    names = [human_name(name.strip()) for name in str(raw_authors or "").split(separator) if name.strip()]
    rendered = [r"\textbf{Hyeonsu Lyu}" if name == "Hyeonsu Lyu" else latex(name) for name in names]
    if len(rendered) < 2:
        return "".join(rendered)
    if len(rendered) == 2:
        return f"{rendered[0]} and {rendered[1]}"
    return f"{', '.join(rendered[:-1])}, and {rendered[-1]}"


def profile_fragment(portfolio: dict, cv: dict) -> str:
    site = require_mapping(portfolio, "site", Path("portfolio.yml"))
    profile = require_mapping(portfolio, "profile", Path("portfolio.yml"))
    links = profile.get("links", {})
    name_parts = str(site.get("name", "")).split()
    if len(name_parts) < 2:
        raise ValueError("portfolio.yml: site.name must include given and family names")

    homepage = str(site.get("url", "")).removeprefix("https://").removeprefix("http://").rstrip("/")
    github = urlparse(str(links.get("github", ""))).path.strip("/")
    linkedin = urlparse(str(links.get("linkedin", ""))).path.strip("/").removeprefix("in/")
    scholar_query = parse_qs(urlparse(str(links.get("scholar", ""))).query)
    scholar_id = scholar_query.get("user", [""])[0]
    email_display = str(cv.get("email_display") or profile.get("email", ""))
    email_display_tex = "".join(
        f"\\textcolor{{awesome}}{{{latex(part)}}}" if part == "dot" else latex(part)
        for part in re.split(r"(\bdot\b)", email_display)
    )

    lines = [
        f"\\name{{{latex(' '.join(name_parts[:-1]))}}}{{{latex(name_parts[-1])}}}",
        f"\\newcommand{{\\generatedcvname}}{{{latex(site['name'])}}}",
        f"\\position{{{latex(cv.get('position', ''))}}}",
        f"\\address{{{latex(cv.get('address', ''))}}}",
        f"\\email{{{email_display_tex}}}",
        f"\\emailtarget{{{latex(profile.get('email', ''))}}}",
        f"\\homepage{{{latex(homepage)}}}",
    ]
    if github:
        lines.append(f"\\github{{{latex(github)}}}")
    if linkedin:
        lines.append(f"\\linkedin{{{latex(linkedin)}}}")
    if scholar_id:
        lines.append(f"\\googlescholar{{{latex(scholar_id)}}}{{Google Scholar}}")
    if cv.get("quote"):
        lines.append(f"\\quote{{``{latex(cv['quote'])}''}}")
    return "\n".join(lines) + "\n"


def cv_entry(
    position: object,
    title: object,
    location: object,
    period: object,
    description: object = "",
    description_is_tex: bool = False,
) -> str:
    rendered_description = description if description_is_tex else latex(description)
    return (
        f"  \\cventry\n"
        f"    {{{latex(position)}}}\n"
        f"    {{{latex(title)}}}\n"
        f"    {{{latex(location)}}}\n"
        f"    {{{latex(period)}}}\n"
        f"    {{{rendered_description}}}\n"
    )


def research_profile_section(portfolio: dict, cv: dict, _: list[dict]) -> str:
    interests = cv.get("field_of_interest", [])
    highlights = [
        {"label": "Publications", "text": cv.get("publications_summary", "")},
        *cv.get("summary_highlights", []),
    ]
    lines = [
        r"\cvsection{Summary}\par",
        r"\begin{cvparagraph}",
        latex(cv.get("research_profile", "")),
        r"\end{cvparagraph}",
        r"\cventry",
        r"  {}",
        r"  {Highlights\vspace{-0.3cm}}",
        r"  {}",
        r"  {}",
        r"  {",
        r"    \begin{cvitems}",
    ]
    for item in highlights:
        details = item.get("items") or [item.get("text", "")]
        lines.extend([f"      \\item {latex(item.get('label', ''))}:", r"        \begin{itemize}"])
        for detail in details:
            if isinstance(detail, dict):
                rendered_detail = latex(detail.get("text", ""))
                if detail.get("url"):
                    link_text = detail.get("link_text") or detail["url"]
                    rendered_detail += f" \\href{{{url_argument(detail['url'])}}}{{\\textcolor{{awesome}}{{{latex(link_text)}}}}}"
            else:
                rendered_detail = latex(detail)
            lines.append(f"          \\item {rendered_detail}")
        lines.append(r"        \end{itemize}")
    lines.extend([
        r"    \end{cvitems}",
        r"  }",
        r"\par\vspace{4mm}",
        r"\cventry",
        r"  {My research interests include, but are not confined to:}",
        r"  {Field of Interest}",
        r"  {}",
        r"  {}",
        r"  {",
        r"    \begin{cvitems}",
    ])
    lines.extend(f"      \\item {latex(interest)}" for interest in interests)
    lines.extend([r"    \end{cvitems}", r"  }", r"\par", ""])
    return "\n".join(lines)


def education_section(portfolio: dict, cv: dict, _: list[dict]) -> str:
    education = require_mapping(portfolio, "experience", Path("portfolio.yml")).get("education", [])
    lines = [r"\cvsection{Education}", r"\begin{cventries}"]
    for item in education:
        degree = f"{item.get('degree', '')} in {item.get('field', '')}".strip()
        description_parts = []
        thesis = item.get("dissertation") or item.get("thesis")
        if thesis:
            label = "Dissertation" if item.get("dissertation") else "Thesis"
            description_parts.append(f"\\item {label}: ``{latex(thesis)}''.")
        if item.get("adviser"):
            description_parts.append(f"\\item Advised by {latex(item['adviser'])}.")
        description = ""
        if description_parts:
            description = "\\vspace{-5mm}\\begin{itemize}[leftmargin=*,nosep,topsep=0pt,partopsep=0pt]" + "".join(description_parts) + "\\end{itemize}"
        school = cv.get("institution_names", {}).get(item.get("school"), item.get("school"))
        lines.append(cv_entry(degree, school, item.get("location"), item.get("period"), description, description_is_tex=True))
    lines.append(r"\end{cventries}")
    return "\n".join(lines) + "\n"


def experience_section(portfolio: dict, _: dict, __: list[dict]) -> str:
    jobs = require_mapping(portfolio, "experience", Path("portfolio.yml")).get("professional", [])
    lines = [r"\cvsection{Working Experience}", r"\begin{cventries}"]
    for job in jobs:
        organization = job.get("organization", "")
        if job.get("unit"):
            organization = f"{organization}, {job['unit']}"
        contributions = job.get("contributions", [])
        description = ""
        if contributions:
            items = "".join(f"\\item {latex(item)}" for item in contributions)
            description = f"\\vspace{{-5mm}}\\begin{{itemize}}[leftmargin=*,nosep,topsep=0pt,partopsep=0pt]{items}\\end{{itemize}}"
        lines.append(
            cv_entry(
                organization,
                job.get("title"),
                job.get("location"),
                job.get("period"),
                description,
                description_is_tex=True,
            )
        )
    lines.append(r"\end{cventries}")
    return "\n".join(lines) + "\n"


def publication_line(entry: dict) -> str:
    authors = author_list(entry.get("author"))
    title = bib_text(entry.get("title"))
    url = entry.get("url") or (f"https://doi.org/{entry['doi']}" if entry.get("doi") else "")
    linked_title = f"\\href{{{url_argument(url)}}}{{{title}}}" if url else title
    venue = bib_text(entry.get("abbr") or entry.get("journal") or entry.get("booktitle"))
    year = bib_text(entry.get("year"))
    note = bib_text(entry.get("note"))
    ending = f" {note}." if note else ""
    return f"  \\item {authors}, ``{linked_title},'' \\textit{{{venue}}}, {year}.{ending}"


def publications_section(_: dict, __: dict, bibliography: list[dict]) -> str:
    groups = [
        ("International Journals", [entry for entry in bibliography if entry.get("ENTRYTYPE") == "article" and entry.get("abbr") != "arXiv"]),
        ("International Conferences and Workshops", [entry for entry in bibliography if entry.get("ENTRYTYPE") == "inproceedings"]),
        ("Preprints", [entry for entry in bibliography if entry.get("abbr") == "arXiv"]),
    ]
    lines = [r"\cvsection{Publications}", r"\par"]
    for heading, entries in groups:
        if not entries:
            continue
        lines.extend([f"\\cvsubsection{{{heading}}}", r"\begin{pubSubsectionNum}"])
        lines.extend(publication_line(entry) for entry in entries)
        lines.append(r"\end{pubSubsectionNum}")
    return "\n".join(lines) + "\n"


def domestic_papers_section(portfolio: dict, _: dict, __: list[dict]) -> str:
    papers = require_mapping(portfolio, "miscellaneous", Path("portfolio.yml")).get("domestic_papers", [])
    lines = [r"\cvsection{Domestic Papers}", r"\begin{pubSubsectionNum}"]
    for paper in papers:
        authors = author_list(paper.get("authors"), separator=";")
        note = f" {latex(paper['note'])}." if paper.get("note") else ""
        lines.append(
            f"  \\item {authors}, ``{latex(paper.get('title'))},'' \\textit{{{latex(paper.get('venue'))}}}, {latex(paper.get('date'))}.{note}"
        )
    lines.append(r"\end{pubSubsectionNum}")
    return "\n".join(lines) + "\n"


def intellectual_properties_section(portfolio: dict, _: dict, __: list[dict]) -> str:
    miscellaneous = require_mapping(portfolio, "miscellaneous", Path("portfolio.yml"))
    lines = [r"\cvsection{Intellectual Properties}"]
    patents = miscellaneous.get("patents", [])
    if patents:
        lines.extend([r"\cvsubsection{Patents}", r"\begin{pubSubsectionNum}"])
        for patent in patents:
            identifiers = [f"{patent.get('jurisdiction', '')} {patent.get('application', '')}".strip()]
            if patent.get("registration"):
                identifiers.append(f"Registration {patent['registration']}")
            lines.append(
                f"  \\item {author_list(patent.get('inventors'), separator=';')}, ``{latex(patent.get('title'))},'' {latex('; '.join(identifiers))}. {latex(patent.get('status'))}."
            )
        lines.append(r"\end{pubSubsectionNum}")
    return "\n".join(lines) + "\n"


def awards_section(portfolio: dict, cv: dict, __: list[dict]) -> str:
    awards = require_mapping(portfolio, "experience", Path("portfolio.yml")).get("awards", [])
    excluded_awards = set(cv.get("excluded_awards", []))
    lines = [r"\cvsection{Awards \& Honors}", r"\begin{cvhonors}"]
    for award in awards:
        if award.get("title") in excluded_awards:
            continue
        date = award.get("date", award.get("year"))
        organization_and_date = f"{award.get('organization')}, {date}"
        lines.append(f"  \\cvhonorfull{{{latex(award.get('title'))}}}{{{latex(organization_and_date)}}}{{}}")
    lines.append(r"\end{cvhonors}")
    return "\n".join(lines) + "\n"


def abbreviation(value: object) -> str:
    text = str(value or "")
    match = re.search(r"\(([^()]+)\)\s*$", text)
    return match.group(1) if match else text


def key_projects_section(portfolio: dict, _: dict, __: list[dict]) -> str:
    projects = require_mapping(portfolio, "miscellaneous", Path("portfolio.yml")).get("projects", [])
    lines = [r"\cvsection{Key Research Projects Experience}", r"\begin{cventries}"]
    for project in projects:
        sponsors = [abbreviation(project.get("ministry")), abbreviation(project.get("agency")), str(project.get("acknowledge", ""))]
        support = ", ".join(part for part in sponsors if part and part != "N/A")
        description_parts = [f"\\item {latex(item)}" for item in project.get("contributions", [])]
        keywords = project.get("keywords")
        if keywords:
            description_parts.append(f"\\item \\textit{{Keywords:}} {latex(keywords)}")
        description = ""
        if description_parts:
            description = "\\vspace{-5mm}\\begin{itemize}[leftmargin=*,nosep,topsep=0pt,partopsep=0pt]" + "".join(description_parts) + "\\end{itemize}"
        lines.append(cv_entry(support, project.get("title"), "", project.get("period"), description, description_is_tex=True))
    lines.append(r"\end{cventries}")
    return "\n".join(lines) + "\n"


def academic_services_section(portfolio: dict, _: dict, __: list[dict]) -> str:
    experience = require_mapping(portfolio, "experience", Path("portfolio.yml"))
    lines = [r"\cvsection{Academic Services}", r"\par", r"\cvsubsection{Reviewer}", r"\begin{cvhonors}"]
    for venue in experience.get("reviewer", []):
        lines.append(f"  \\cvhonorworanking{{{latex(venue.get('name'))}}}{{}}{{{latex(venue.get('years'))}}}")
    lines.append(r"\end{cvhonors}")
    localization = experience.get("other_service", {}).get("localization", [])
    if localization:
        lines.extend([r"\cvsubsection{Open Source and Localization}", r"\begin{cvhonors}"])
        for item in localization:
            title = item.get("title", "")
            if item.get("contribution"):
                title = f"{title}, {item['contribution']}"
            lines.append(f"  \\cvhonorworanking{{{latex(title)}}}{{}}{{{latex(item.get('years'))}}}")
        lines.append(r"\end{cvhonors}")
    return "\n".join(lines) + "\n"


def talks_section(portfolio: dict, _: dict, __: list[dict]) -> str:
    talks = require_mapping(portfolio, "experience", Path("portfolio.yml")).get("other_service", {}).get("talks", [])
    lines = [r"\cvsection{Talks}", r"\begin{pubSubsectionNum}"]
    lines.extend(f"  \\item {latex(talk)}" for talk in talks)
    lines.append(r"\end{pubSubsectionNum}")
    return "\n".join(lines) + "\n"


def additional_sections(_: dict, cv: dict, __: list[dict]) -> str:
    lines = []
    for section in cv.get("additional_sections", []):
        lines.extend([f"\\cvsection{{{latex(section.get('title'))}}}", r"\begin{pubSubsectionNum}"])
        lines.extend(f"  \\item {latex(item)}" for item in section.get("items", []))
        lines.append(r"\end{pubSubsectionNum}")
    return "\n".join(lines) + ("\n" if lines else "")


SECTION_RENDERERS = {
    "research_profile": research_profile_section,
    "education": education_section,
    "experience": experience_section,
    "publications": publications_section,
    "domestic_papers": domestic_papers_section,
    "intellectual_properties": intellectual_properties_section,
    "awards": awards_section,
    "key_projects": key_projects_section,
    "academic_services": academic_services_section,
    "talks": talks_section,
    "additional_sections": additional_sections,
}


def render(portfolio_path: Path, bibliography_path: Path, extra_path: Path, output_directory: Path) -> None:
    portfolio = read_yaml(portfolio_path)
    extra = read_yaml(extra_path)
    cv = require_mapping(extra, "cv", extra_path)
    bibliography = read_bibliography(bibliography_path)
    order = cv.get("section_order", [])
    if not isinstance(order, list) or not order:
        raise ValueError(f"{extra_path}: cv.section_order must be a non-empty list")
    unknown = set(order) - SECTION_KEYS
    if unknown:
        raise ValueError(f"{extra_path}: unknown section keys: {', '.join(sorted(unknown))}")
    if len(order) != len(set(order)):
        raise ValueError(f"{extra_path}: cv.section_order contains duplicates")

    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "profile.tex").write_text(profile_fragment(portfolio, cv), encoding="utf-8")
    sections = "\n".join(SECTION_RENDERERS[key](portfolio, cv, bibliography) for key in order)
    (output_directory / "sections.tex").write_text(sections, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", required=True, type=Path)
    parser.add_argument("--bibliography", required=True, type=Path)
    parser.add_argument("--extra", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    render(args.portfolio, args.bibliography, args.extra, args.output)


if __name__ == "__main__":
    main()
