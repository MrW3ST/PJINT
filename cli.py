#!/usr/bin/env python3
"""
PJINT CLI — Extraction Pages Jaunes en ligne de commande.

Usage :
    python cli.py --ville Lyon --keyword plombier
    python cli.py --ville Paris --keyword __restauration --format json -o resultats.json
    python cli.py --ville Nantes --keyword association --format excel
"""

import argparse
import asyncio
import csv
import io
import json
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
    _RICH = True
except ImportError:
    _RICH = False

import scraper

# ── Affichage ──────────────────────────────────────────────────────────────────

GROUPS_DISPLAY = {
    "__restauration":  "Toute la Restauration",
    "__alimentation":  "Toute l'Alimentation",
    "__sante_medecin": "Tous les Médecins",
    "__sante_para":    "Toute la Para-médecine",
    "__sante_etab":    "Tous les Établissements de Santé",
    "__beaute":        "Toute la Beauté",
    "__sport":         "Tout le Sport",
    "__hotellerie":    "Toute l'Hôtellerie",
    "__education":     "Toute l'Éducation",
    "__informatique":  "Tout l'Informatique",
    "__artisans":      "Tous les Artisans",
    "__automobile":    "Tout l'Automobile",
    "__commerce":      "Tout le Commerce",
    "__services_pers": "Tous les Services à la Personne",
    "__liberales":     "Toutes les Professions Libérales",
    "__immobilier":    "Tout l'Immobilier",
    "__transport":     "Tout le Transport",
    "__funeraire":     "Tout le Funéraire",
    "__animaux":       "Tous les Animaux",
    "__loisirs":       "Tous les Loisirs",
    "__tout":          "Toutes les catégories",
}


def keyword_label(kw: str) -> str:
    return GROUPS_DISPLAY.get(kw, kw)


# ── Export final (Excel uniquement, CSV/JSON sont écrits progressivement) ──────

def export_excel(results: list[dict], path: str) -> None:
    try:
        import openpyxl
    except ImportError:
        print("openpyxl not installed. Run:  pip install openpyxl", file=sys.stderr)
        sys.exit(1)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Résultats"
    ws.append(["Nom", "Téléphone", "Adresse", "Catégorie"])
    for r in results:
        ws.append([r.get("nom", ""), r.get("telephone", ""), r.get("adresse", ""), r.get("categorie", "")])
    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)
    wb.save(path)


# ── Writer progressif ──────────────────────────────────────────────────────────

ALL_FIELDS = ["nom", "telephone", "adresse", "categorie"]


class ProgressiveWriter:
    """Écrit les résultats au fur et à mesure dans le fichier de sortie."""

    def __init__(self, path: str, fmt: str, fields: list[str]):
        self.path   = path
        self.fmt    = fmt
        self.fields = fields
        self._f     = None
        self._csv   = None
        self._buf: list[dict] = []   # Excel uniquement

    def _pick(self, item: dict) -> dict:
        return {k: item.get(k, "") for k in self.fields}

    def open(self) -> None:
        if self.fmt == "csv":
            self._f = open(self.path, "w", newline="", encoding="utf-8-sig")
            self._csv = csv.DictWriter(self._f, fieldnames=self.fields)
            self._csv.writeheader()
        elif self.fmt == "json":
            self._f = open(self.path, "w", encoding="utf-8")
            self._f.write("[\n")
        elif self.fmt == "txt":
            self._f = open(self.path, "w", encoding="utf-8")
        # excel : on accumule en mémoire

    def write(self, items: list[dict]) -> None:
        if self.fmt == "csv" and self._csv:
            self._csv.writerows(self._pick(r) for r in items)
            self._f.flush()
        elif self.fmt == "json" and self._f:
            for item in items:
                if self._f.tell() > 2:
                    self._f.write(",\n")
                self._f.write("  " + json.dumps(self._pick(item), ensure_ascii=False))
            self._f.flush()
        elif self.fmt == "txt" and self._f:
            for item in items:
                line = " | ".join(item.get(k, "") for k in self.fields)
                self._f.write(line + "\n")
            self._f.flush()
        elif self.fmt == "excel":
            self._buf.extend(items)

    def close(self, total: int) -> None:
        if self.fmt == "csv" and self._f:
            self._f.close()
            print(f"\nCSV saved → {self.path}  ({total} entries)")
        elif self.fmt == "json" and self._f:
            self._f.write("\n]\n")
            self._f.close()
            print(f"\nJSON saved → {self.path}  ({total} entries)")
        elif self.fmt == "txt" and self._f:
            self._f.close()
            print(f"\nTXT saved → {self.path}  ({total} entries)")
        elif self.fmt == "excel":
            export_excel(self._buf, self.path)
            print(f"\nExcel saved → {self.path}  ({total} entries)")


# ── Runner principal ───────────────────────────────────────────────────────────

async def run(ville: str, keyword: str, output: str, fmt: str, fields: list[str], quiet: bool) -> int:
    """Lance le scraping avec sauvegarde progressive. Retourne le nombre d'entrées."""
    writer = ProgressiveWriter(output, fmt, fields)
    writer.open()
    total_found  = 0
    total_pages  = 1

    try:
        if _RICH and not quiet:
            console = Console()
            console.print(f"\n[bold cyan]PJINT[/] — [white]{keyword_label(keyword)}[/] à [white]{ville}[/]")
            console.print(f"[dim]Output → {output}[/]\n")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TextColumn("[cyan]{task.fields[extra]}"),
                console=console,
                transient=False,
            ) as progress:
                task = progress.add_task("Starting…", total=None, extra="")

                async for event in scraper.scrape(ville, keyword):
                    t = event.get("type")

                    if t == "status":
                        progress.update(task, description=event["msg"])
                    elif t == "keyword_start":
                        kw_label = f"[{event['kw_index']}/{event['kw_total']}] {event['keyword']}"
                        progress.update(task, description=kw_label, total=None, completed=0, extra="")
                    elif t == "info":
                        total_pages = event["total_pages"]
                        pj_total = event.get("total_results", 0)
                        extra = f"  ~{pj_total} entries" if pj_total else ""
                        progress.update(task, total=total_pages, completed=0, extra=extra)
                    elif t == "results":
                        writer.write(event["items"])
                        total_found = event["total_found"]
                        progress.update(task, completed=event["page"],
                                        extra=f"  {total_found} saved")
                    elif t in ("error", "warn"):
                        console.print(f"[{'red' if t == 'error' else 'yellow'}]{event['msg']}[/]")
                    elif t == "done":
                        total_found = event["total"]
                        progress.update(task, description="Done", completed=total_pages or 1,
                                        total=total_pages or 1, extra=f"  {total_found} entries")

            console.print()

        else:
            async for event in scraper.scrape(ville, keyword):
                t = event.get("type")
                if t == "status" and not quiet:
                    print(f"[*] {event['msg']}")
                elif t == "keyword_start" and not quiet:
                    print(f"\n── [{event['kw_index']}/{event['kw_total']}] {event['keyword']} ──")
                elif t == "info" and not quiet:
                    pj_total = event.get("total_results", 0)
                    total_pages = event["total_pages"]
                    if pj_total:
                        print(f"    ~{pj_total} entries · {total_pages} pages")
                elif t == "results":
                    writer.write(event["items"])
                    total_found = event["total_found"]
                    if not quiet:
                        print(f"    p.{event['page']}/{event['total_pages']} · {total_found} saved", end="\r")
                elif t in ("error", "warn") and not quiet:
                    print(f"\n[{'ERROR' if t == 'error' else 'WARN'}] {event['msg']}", file=sys.stderr)
                elif t == "done":
                    total_found = event["total"]
                    if not quiet:
                        print(f"\nDone — {total_found} entries total")

    except KeyboardInterrupt:
        if not quiet:
            print(f"\n\nInterrupted — {total_found} entries saved so far.")
    finally:
        writer.close(total_found)

    return total_found


# ── Entrypoint ─────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pjint",
        description="PJINT — Pages Jaunes scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python cli.py --ville Lyon --keyword plombier
  python cli.py --ville Paris --keyword __restauration -o restaurants.csv
  python cli.py --ville Nantes --keyword association --format json -o assoc.json
  python cli.py --ville Bordeaux --keyword __artisans --format excel -o artisans.xlsx

available groups:
  __restauration  __alimentation  __sante_medecin  __sante_para
  __sante_etab    __beaute        __sport           __hotellerie
  __education     __informatique  __artisans        __automobile
  __commerce      __services_pers __liberales       __immobilier
  __transport     __funeraire     __animaux         __loisirs
  __tout          (all categories)
        """,
    )
    p.add_argument("--ville",   "-v", required=True, metavar="CITY",   help="city to scrape (e.g. Lyon, Paris 75001)")
    p.add_argument("--keyword", "-k", required=True, metavar="CATEG",  help="category or group (e.g. plombier, __artisans)")
    p.add_argument("--output",  "-o", default=None,  metavar="FILE",   help="output file (optional, defaults to stdout)")
    p.add_argument("--format",  "-f", default="csv",
                   choices=["csv", "json", "excel", "txt"], metavar="FORMAT",
                   help="export format: csv (default), json, excel, txt")
    p.add_argument("--fields", default=None, metavar="FIELDS",
                   help="comma-separated fields to export: nom,telephone,adresse,categorie (default: all). "
                        "e.g. --fields telephone  →  one number per line")
    p.add_argument("--quiet",        "-q", action="store_true", help="suppress progress output")
    p.add_argument("--list-groups",        action="store_true", help="list available groups and exit")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_groups:
        print("Groupes disponibles :\n")
        for key, label in GROUPS_DISPLAY.items():
            print(f"  {key:<20}  {label}")
        print()
        sys.exit(0)

    # Valide et résout --fields
    if args.fields:
        fields = [f.strip() for f in args.fields.split(",")]
        invalid = [f for f in fields if f not in ALL_FIELDS]
        if invalid:
            build_parser().error(f"unknown field(s): {', '.join(invalid)}. Choose from: {', '.join(ALL_FIELDS)}")
    else:
        fields = ALL_FIELDS

    # Génère toujours un nom de fichier (jamais de stdout pour éviter les pertes)
    ext_map = {"csv": ".csv", "json": ".json", "excel": ".xlsx", "txt": ".txt"}
    if args.output:
        output = args.output
    else:
        safe_ville   = args.ville.replace(" ", "_").lower()
        safe_keyword = args.keyword.replace(" ", "_").lstrip("_")
        output = f"pjint_{safe_ville}_{safe_keyword}{ext_map[args.format]}"
        if not args.quiet:
            print(f"Output file: {output}")

    asyncio.run(run(args.ville, args.keyword, output, args.format, fields, args.quiet))


if __name__ == "__main__":
    main()
