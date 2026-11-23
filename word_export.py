"""Generate a Word document from the same lines used by the plain-text export."""
from io import BytesIO
import re
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


CONTENT_TYPES = """<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Override PartName="/word/document.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
RELATIONSHIPS = """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
 Target="word/document.xml"/>
</Relationships>"""
INVALID_XML = re.compile(r"[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")


def render_docx(header: list[str], transcript: list[str]) -> bytes:
    document = ET.Element("w:document", {
        "xmlns:w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    })
    body = ET.SubElement(document, "w:body")
    for line in ["Расшифровка", *header, *transcript]:
        paragraph = ET.SubElement(body, "w:p")
        run = ET.SubElement(paragraph, "w:r")
        for index, part in enumerate(INVALID_XML.sub("\ufffd", line).splitlines() or [""]):
            if index:
                ET.SubElement(run, "w:br")
            for column, text in enumerate(part.split("\t")):
                if column:
                    ET.SubElement(run, "w:tab")
                ET.SubElement(run, "w:t", {"xml:space": "preserve"}).text = text

    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", RELATIONSHIPS)
        archive.writestr("word/document.xml", ET.tostring(document, encoding="utf-8", xml_declaration=True))
    return output.getvalue()
