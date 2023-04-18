import src.data.xml_extraction as xmle
from xml.etree import ElementTree as ET
import glob
import pytest

@pytest.fixture()
def xml_roots():
    xml_roots = []
    for xml in glob.glob("tests\\small_*.xml"):
        tree = ET.parse(xml)
        root = tree.getroot()
        xml_roots.append(root)
    return xml_roots

four_region_xml = ET.parse("tests\\4_TextRegion_xml_example.xml")
four_region_root = four_region_xml.getroot()


def test_extractLines(xml_roots):
    lines = xmle.extractLines(xml_roots[0])

    assert len(lines) == 3
    assert lines[0] == "Test line 1"


def test_extractLines_TextRegion_order():
    ordered_lines = xmle.extractLines(four_region_root)

    assert ordered_lines[0] == "Test line 1"
    assert ordered_lines[3] == "Test line 4"


def test_extractLinesForVol(xml_roots):
    allLines = xmle.extractLinesForVol(xml_roots)

    assert len(allLines) == 6
    assert allLines[-1] == "Test line 6"


def test_checkLine():
    I_num_check = xmle.checkLine("IA. 33")
    C_num_check = xmle.checkLine("C.44")
    bad_check = xmle.checkLine("asdf")

    assert I_num_check
    assert C_num_check
    assert not bad_check


def test_dateCheck():
    date_check = xmle.dateCheck("1409")
    untitled_check = xmle.dateCheck("Undated")
    bad_check = xmle.dateCheck("0300")

    assert date_check
    assert untitled_check
    assert not bad_check


def test_findHeadings(xml_roots):
    allLines = xmle.extractLinesForVol(xml_roots)
