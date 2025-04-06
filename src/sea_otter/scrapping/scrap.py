from bs4 import BeautifulSoup
import requests


class HtmlError(Exception):
    """Exception for non-200 html response."""


def get_html(url: str) -> str:
    response = requests.get(url)
    if response.status_code == 200:
        html_doc = response.text
    else:
        print(f"Failed to retrieve page. Status code: {response.status_code}")
        raise HtmlError()
    return html_doc


def get_links(soup: BeautifulSoup) -> list[str]:
    return [link.get("href") for link in soup.find_all("a")]


def get_raw_tex():
    # Grab the raw text of html page
    pass


def get_pdf_report():
    # Get a pdf version of the page, often linked separately
    pass


def get_json_links():
    # Get just the structured data artifacts
    pass


if __name__ == "__main__":
    url = "https://www.cisa.gov/news-events/analysis-reports/ar25-087a"
    html_doc = get_html(url)
    soup = BeautifulSoup(html_doc, "html.parser")
    print(soup.prettify())
    print(soup.title)
    print(soup.a)
    links = get_links(soup)
    print(soup.get_text())
