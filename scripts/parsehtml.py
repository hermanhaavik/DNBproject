import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

AZURE_FORMRECOGNIZER_SERVICE = os.environ.get("AZURE_FORMRECOGNIZER_SERVICE")
AZURE_FORMRECOGNIZER_KEY = os.environ.get("AZURE_FORMRECOGNIZER_KEY")
assert(AZURE_FORMRECOGNIZER_SERVICE)
assert(AZURE_FORMRECOGNIZER_KEY)

PAGE_URL = "https://dnb.no/forsikring/bilforsikring"

def azure_parse_html():
    formrecognizer_creds = AzureKeyCredential(AZURE_FORMRECOGNIZER_KEY)
    form_recognizer_client = DocumentAnalysisClient(endpoint=f"https://{AZURE_FORMRECOGNIZER_SERVICE}.cognitiveservices.azure.com/", credential=formrecognizer_creds, headers={"x-ms-useragent": "azure-search-chat-demo/1.0.0"}, api_version="2023-02-28-preview")

    poller = form_recognizer_client.begin_analyze_document_from_url("prebuilt-read", PAGE_URL)
    result = poller.result()
    all_content = result.paragraphs and '\n'.join([p.content for p in result.paragraphs]) or []

    return all_content

def beautifulsoup_parse_html():
    req = Request(PAGE_URL)
    html_page = urlopen(req).read()
    soup = BeautifulSoup(html_page, "html.parser")

    result = ""

    for section in soup.select("div[data-section-index]"):
        section_type = section["data-section-type"]
        section_text = ""
        if section_type in ["pageTitle", "text"]:
            # TODO: Handle hyperlinks
            section_text = section.get_text(strip=True, separator=": ")
        elif section_type == "faqs":
            heading = section.find("h2")
            if heading:
                section_text += heading.get_text(strip=True)
            for qa in section.select("div[class*='dnb-accordion']"):
                question = qa.find("div[class*='dnb-accordion__header']")
                if question:
                    section_text = "\n".join([section_text, question.get_text(strip=True)])
                for elem in qa.find_all(["h3", "ul", "p"]):
                    if elem.name == "ul":
                        for item in elem.find_all("li"):
                            section_text += f"\n- {item.get_text(strip=True)}"
                    else:
                        section_text = "\n".join([section_text, elem.get_text(strip=True)])
        elif section_type == "comparisonTable":
            table_html = "<table>"
            table = section.find("table")
            for row in table.find_all("tr"):
                table_html += "<tr>"
                for cell in row.find_all(["td", "th"]):
                    table_html += f"<{cell.name}>"
                    content = cell.get_text(strip=True)
                    # Some cells use checkmarks instead of text
                    if len(content) == 0 and cell.find("svg"):
                        content = "X"
                    table_html += content
                    table_html += f"</{cell.name}>"
                table_html += "</tr"
            table_html += "</table>"

            section_text = table_html

        result = "\n".join([result, section_text])

    return result

beautifulsoup_parse_html()
