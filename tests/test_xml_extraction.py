import src.data.xml_extraction as xmle
from xml.etree import ElementTree as ET
import glob
import pytest
from tqdm import tqdm
from functools import partialmethod

tqdm.__init__ = partialmethod(tqdm.__init__, disable=True)


@pytest.fixture()
def xml_roots():
    xml_roots = []
    for xml in glob.glob("tests\\small_*.xml"):
        tree = ET.parse(xml)
        root = tree.getroot()
        xml_roots.append(root)
    return xml_roots


def test_extract_lines(xml_roots):
    lines = xmle.extract_lines(xml_roots[0])

    assert len(lines) == 3
    assert lines[0] == "Test line 1"


def test_extract_lines_text_region_order():
    four_region_xml = ET.parse("tests\\4_TextRegion_xml_example.xml")
    four_region_root = four_region_xml.getroot()
    ordered_lines = xmle.extract_lines(four_region_root)

    assert ordered_lines[0] == "Test line 1"
    assert ordered_lines[3] == "Test line 4"


def test_extract_lines_for_vol(xml_roots):
    allLines = xmle.extract_lines_for_vol(xml_roots)

    assert len(allLines) == 6
    assert allLines[-1] == "Test line 6"


def test_check_line():
    i_num_check = xmle.check_line("IA. 33")
    c_num_check = xmle.check_line("C.44")
    bad_check = xmle.check_line("asdf")

    assert i_num_check
    assert c_num_check
    assert not bad_check


def test_date_check():
    date_check = xmle.date_check("1409")
    untitled_check = xmle.date_check("Undated")
    bad_check = xmle.date_check("0300")

    assert date_check
    assert untitled_check
    assert not bad_check


@pytest.fixture()
def lines_titles_indices():
    in_xml = ET.parse("tests\\title_xml_example.xml")
    root = in_xml.getroot()
    allLines = xmle.extract_lines(root)
    titles, allTitleIndices = xmle.find_headings(allLines)
    return allLines, titles, allTitleIndices


def test_find_headings(xml_roots, lines_titles_indices):
    all_lines = xmle.extract_lines_for_vol(xml_roots)
    no_titles, no_all_title_indices = xmle.find_headings(all_lines)
    # should both be empty
    assert not no_titles
    assert not no_all_title_indices

    """"
    the xml used to make title_indices contains three IA. numbers that could start titles
    The second IA. (IA. 456) has its title interrupted by IA. 789 before a date is found
    This tests the 
    `if checkLine(titlePart):
    `    break
    section of findHeadings 
    """
    _, titles, all_title_indices = lines_titles_indices

    assert len(titles), len(all_title_indices) == (2, 2)
    assert titles == ["IA. 123TITLE1456", "IA. 789SECONDTITLE1506"]
    assert all_title_indices == [[0, 1, 2], [6, 7, 8]]


def test_get_i_num_title():
    full_title_onestop = "IA. 31234ASDF"
    full_title_twostop = "IA. 31234.ASDF.LKJH"

    title_onestop = xmle.get_i_num_title(full_title_onestop)
    title_twostop = xmle.get_i_num_title(full_title_twostop)

    assert title_onestop == "IA. 31234"
    assert title_twostop == "IA. 31234"


def test_get_c_num_title():
    full_title_onestop = "C. 312341"
    full_title_fourstop = "C.31.a.2.3.ASDF"

    title_onestop = xmle.get_c_num_title(full_title_onestop)
    title_fourstop = xmle.get_c_num_title(full_title_fourstop)

    assert title_onestop == "C. 312341"
    assert title_fourstop == "C.31.a.2"


def test_find_title_ref(capsys):
    full_title_i = "ASDFIB. 1345/"
    full_title_c = "ASDFC.145132/a"
    bad_title = "NOTHINGCAPTUREDHERE"

    foundref_i = xmle.find_title_ref(full_title_i)
    foundref_c = xmle.find_title_ref(full_title_c)

    # next one should print "Unrecognized title format" to stdout
    foundref_bad = xmle.find_title_ref(bad_title)
    captured = capsys.readouterr()

    assert foundref_i == "IB. 1345."
    assert foundref_c == "C.145132.a"
    assert captured.out == "Unrecognized title format\n"


def test_gen_title_refs(lines_titles_indices):
    all_lines, _, all_title_indices = lines_titles_indices
    title_refs = xmle.gen_title_refs(all_title_indices, all_lines)
    # two titles/lists of title indices in lines_titles_indices
    # genTitleRefs selects [:-1] so only get one out
    assert len(title_refs) == 1
    assert title_refs[0] == "IA. 123TI"


def test_generate_xml():
    in_xml = ET.parse("tests\\title_xml_example.xml")
    root = in_xml.getroot()
    all_lines = xmle.extract_lines(root)
    title, all_title_indices = xmle.find_headings(all_lines)

    # out_xml = xmle.generateXML(all_title_indices, all_lines, )