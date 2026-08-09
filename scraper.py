"""Coleta os eventos e mantém um contrato de datas estável no eventos.json.

`data` é o texto exibido. `data_inicio` e `data_fim` são datas ISO usadas pela
interface; nenhuma camada do frontend precisa interpretar o idioma do portal.
"""
import argparse
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


ARQUIVO_EVENTOS = Path(__file__).with_name("eventos.json")
SOURCES = ("fotop", "foco_radical", "fotto")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; divulgador-events/1.0)"}
MONTHS = {
    "jan": 1, "janeiro": 1, "feb": 2, "fev": 2, "fevereiro": 2,
    "mar": 3, "marco": 3, "apr": 4, "abr": 4, "abril": 4,
    "may": 5, "mai": 5, "maio": 5, "jun": 6, "junho": 6,
    "jul": 7, "julho": 7, "aug": 8, "ago": 8, "agosto": 8,
    "sep": 9, "set": 9, "setembro": 9, "oct": 10, "out": 10,
    "outubro": 10, "nov": 11, "novembro": 11, "dec": 12,
    "dez": 12, "dezembro": 12,
}
NUMERIC_DATE = re.compile(r"(?<!\d)(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})(?!\d)")
ISO_DATE = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
TEXT_DATE = re.compile(r"(?<!\d)(\d{1,2})\s*(?:de\s+)?([A-Za-zÀ-ÿ.]+)\s*(?:de\s+)?(\d{4})(?!\d)", re.I)
UNKNOWN_DATES = {"", "data a definir", "data não informada", "data nao informada", "sem data"}


def clean_text(value):
    return " ".join((value or "").split())


def ascii_key(value):
    return unicodedata.normalize("NFD", value.lower()).encode("ascii", "ignore").decode("ascii").rstrip(".")


def iso_date(year, month, day):
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return None


def dates_from_text(value):
    """Extrai datas completas em formatos numérico, ISO e PT/EN abreviado."""
    value = clean_text(value)
    found = []
    for match in ISO_DATE.finditer(value):
        found.append((match.start(), iso_date(*match.groups())))
    for match in NUMERIC_DATE.finditer(value):
        day, month, year = match.groups()
        found.append((match.start(), iso_date(year, month, day)))
    for match in TEXT_DATE.finditer(value):
        day, month_name, year = match.groups()
        month = MONTHS.get(ascii_key(month_name))
        found.append((match.start(), iso_date(year, month, day) if month else None))
    return [item[1] for item in sorted(found) if item[1]]


def normalize_date_text(value):
    """Retorna texto para exibição e limites ISO; não inventa ano ausente."""
    display = clean_text(value)
    if ascii_key(display) in UNKNOWN_DATES:
        return display or "Data não informada", None, None
    parsed = dates_from_text(display)
    if not parsed:
        return display, None, None
    return display, parsed[0], parsed[-1]


def with_normalized_dates(event):
    event = dict(event)
    display, start, end = normalize_date_text(event.get("data", ""))
    event["data"] = display
    if start:
        event["data_inicio"] = start
        event["data_fim"] = end
    else:
        event.pop("data_inicio", None)
        event.pop("data_fim", None)
    return event


def get_soup(url):
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def image_from(node):
    image = node.find("img")
    return image and (image.get("src") or image.get("data-src") or image.get("data-original")) or ""


def first_text(node, selectors, fallback=""):
    for selector in selectors:
        item = node.select_one(selector)
        if item:
            text = clean_text(item.get_text(" ", strip=True))
            if text:
                return text
    return fallback


def find_date_in(node):
    candidates = [node.select_one("time"), *node.select("[class*='date'], [class*='calendar']")]
    candidates.append(node)
    for candidate in candidates:
        if candidate:
            text = clean_text(candidate.get_text(" ", strip=True))
            if dates_from_text(text):
                return text
    return "Data não informada"


def scrape_fotop():
    try:
        soup = get_soup("https://voce.fotop.com/?status=ativo")
        events = []
        for card in soup.select("div.card-evt-busca"):
            anchor = card.find("a", href=True)
            if not anchor:
                continue
            events.append(with_normalized_dates({
                "titulo": first_text(card, [".card-titulo-evento"], "Evento sem título"),
                "data": first_text(card, [".card-data-evento"], "Data não informada"),
                "local": first_text(card, [".nome-cidade-card"], "Brasil"),
                "imagem": image_from(card),
                "link": urljoin("https://voce.fotop.com", anchor["href"]),
            }))
        return events
    except requests.RequestException as error:
        print(f"Erro ao raspar Fotop: {error}")
        return None


def scrape_foco_radical():
    try:
        # A raiz da loja passou a ser institucional. A vitrine de eventos da
        # própria loja é carregada em /site/index pelo frontend atual.
        base_url = "https://vocee.focoradical.com.br/"
        response = requests.get(
            urljoin(base_url, "site/index?language=pt-BR"),
            headers=HEADERS,
            timeout=20,
        )
        response.raise_for_status()

        # O Next.js entrega os eventos como objetos JSON no HTML inicial. Ler
        # esses objetos evita depender de cartões que só aparecem depois de o
        # JavaScript da página ser executado.
        events, seen = [], set()
        decoder = json.JSONDecoder()
        for match in re.finditer(r'"path":"[^"\\]*(?:\\.[^"\\]*)*"', response.text):
            start = response.text.rfind("{", 0, match.start())
            if start < 0:
                continue
            try:
                candidate, _ = decoder.raw_decode(response.text[start:])
            except json.JSONDecodeError:
                continue
            if not isinstance(candidate, dict) or not {"name", "path", "date"} <= candidate.keys():
                continue
            link = urljoin(base_url, f"prova/{candidate['path']}")
            if link in seen:
                continue
            seen.add(link)
            cover = candidate.get("coverPhotoOrIcon") or {}
            events.append(with_normalized_dates({
                "titulo": clean_text(candidate["name"]),
                "data": candidate["date"],
                "local": clean_text(" / ".join(filter(None, [candidate.get("place"), (candidate.get("state") or {}).get("abbreviation")]))) or "Brasil",
                "imagem": cover.get("image") or candidate.get("groupedBannerImage") or "",
                "link": link,
            }))
        if events:
            return events

        # Fallback para o layout antigo da mesma loja, caso ele volte a ser
        # publicado ou a nova vitrine não inclua eventos no HTML.
        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("a[href*='/evento/']")
        cards.extend(node for node in soup.select(".competition") if node not in cards)
        seen = set()
        for card in cards:
            anchor = card if card.name == "a" else card.select_one("a[href]")
            if not anchor:
                continue
            link = urljoin(base_url, anchor["href"])
            if link in seen:
                continue
            seen.add(link)
            local = "Brasil"
            for span in card.select("span, small"):
                text = clean_text(span.get_text(" ", strip=True))
                if "/" in text and not dates_from_text(text):
                    local = text
                    break
            events.append(with_normalized_dates({
                "titulo": first_text(card, ["h2", ".details-name"], "Evento sem título"),
                "data": find_date_in(card),
                "local": local,
                "imagem": image_from(card),
                "link": link,
            }))
        return events
    except requests.RequestException as error:
        print(f"Erro na Foco Radical: {error}")
        return None


def scrape_fotto():
    try:
        base_url = "https://www.fotto.com.br/voce"
        soup = get_soup(base_url)
        events, seen = [], set()
        for card in soup.select(".event-card"):
            anchor = card if card.name == "a" else card.find_parent("a", href=True)
            if not anchor:
                continue
            link = urljoin(base_url, anchor["href"])
            if link in seen:
                continue
            seen.add(link)
            location = first_text(card, [".event-card-location"], "Brasil")
            location = clean_text(re.split(r"[•·]", location)[0]) or "Brasil"
            events.append(with_normalized_dates({
                "titulo": first_text(card, [".event-card-title", "h3"], "Evento sem título"),
                # A data extraída é a data do evento. Nunca a data da coleta.
                "data": first_text(card, [".event-card-date"], "Data não informada"),
                "local": location,
                "imagem": image_from(card),
                "link": link,
            }))
        return events
    except requests.RequestException as error:
        print(f"Erro na Fotto: {error}")
        return None


def repair_fotto_dates(events):
    """Confirma o histórico da Fotto na página do evento, quando solicitado.

    Cartões antigos podem já não aparecer na página inicial. A descrição Open
    Graph de cada página contém a data real e é uma fonte mais confiável do
    que a antiga data de primeira coleta.
    """
    repaired = []
    for event in events:
        updated = dict(event)
        try:
            soup = get_soup(event["link"])
            description = soup.select_one("meta[property='og:description'], meta[name='description']")
            raw_date = description.get("content", "") if description else ""
            display, start, end = normalize_date_text(raw_date)
            if start:
                updated["data"] = f"{start[8:10]}/{start[5:7]}/{start[:4]}"
                updated["data_inicio"] = start
                updated["data_fim"] = end
            else:
                print(f"Data não encontrada na página Fotto: {event['link']}")
        except (KeyError, requests.RequestException) as error:
            print(f"Não foi possível confirmar data Fotto ({event.get('link', 'sem link')}): {error}")
        repaired.append(with_normalized_dates(updated))
    return repaired


def load_existing():
    try:
        with ARQUIVO_EVENTOS.open(encoding="utf-8") as file:
            raw = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        print(f"Não foi possível ler eventos existentes: {error}")
        raw = {}
    return {source: [with_normalized_dates(event) for event in raw.get(source, [])] for source in SOURCES}


def merge_events(existing, scraped):
    """Atualiza o que foi encontrado sem apagar histórico quando um portal falha."""
    if scraped is None:
        return existing
    by_link = {event.get("link"): event for event in existing if event.get("link")}
    result = []
    for fresh in scraped:
        previous = by_link.pop(fresh.get("link"), {})
        merged = {**previous, **fresh}
        # Uma mudança de layout não pode apagar uma data já válida.
        if not fresh.get("data_inicio") and previous.get("data_inicio"):
            merged.update({key: previous[key] for key in ("data", "data_inicio", "data_fim") if key in previous})
        result.append(with_normalized_dates(merged))
    return result + list(by_link.values())


def build_data(existing, scrape=True):
    results = {source: None for source in SOURCES}
    if scrape:
        results = {"fotop": scrape_fotop(), "foco_radical": scrape_foco_radical(), "fotto": scrape_fotto()}
        # A vitrine da Fotto não informa mais a data da prova. Confirma cada
        # evento na página individual antes de atualizar o JSON.
        if results["fotto"] is not None:
            results["fotto"] = repair_fotto_dates(results["fotto"])
    return {source: merge_events(existing[source], results[source]) for source in SOURCES}


def self_test():
    cases = {
        "12/07/2026": ("2026-07-12", "2026-07-12"),
        "01/05/2026 - 04/05/2026": ("2026-05-01", "2026-05-04"),
        "03 MAI 2026": ("2026-05-03", "2026-05-03"),
        "3 de outubro de 2026": ("2026-10-03", "2026-10-03"),
        "2026-12-31": ("2026-12-31", "2026-12-31"),
        "Data a definir": (None, None),
    }
    for raw, expected in cases.items():
        _, start, end = normalize_date_text(raw)
        assert (start, end) == expected, (raw, start, end)
    print(f"OK: {len(cases)} formatos de data validados.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrate-only", action="store_true", help="Estrutura o JSON sem consultar portais.")
    parser.add_argument("--dry-run", action="store_true", help="Consulta portais sem gravar o JSON.")
    parser.add_argument("--self-test", action="store_true", help="Valida a normalização de datas.")
    parser.add_argument("--repair-fotto-dates", action="store_true", help="Confirma o histórico Fotto nas páginas dos eventos.")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    data = build_data(load_existing(), scrape=not args.migrate_only)
    if args.repair_fotto_dates:
        data["fotto"] = repair_fotto_dates(data["fotto"])
    if args.dry_run:
        print("Simulação concluída; nenhum arquivo foi alterado.")
        return
    with ARQUIVO_EVENTOS.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")
    print("Sucesso! " + " | ".join(f"{source}: {len(events)}" for source, events in data.items()))


if __name__ == "__main__":
    main()
