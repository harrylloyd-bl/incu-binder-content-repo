import src.data.xml_extraction as xmle
from xml.etree import ElementTree as ET
import os
import glob
import pytest
from tqdm import tqdm
from functools import partialmethod

tqdm.__init__ = partialmethod(tqdm.__init__, disable=True)


@pytest.fixture()
def xml_roots():
    xml_roots = {}
    for xml in glob.glob("tests\\small_*.xml"):
        tree = ET.parse(xml)
        root = tree.getroot()
        xml_roots[os.path.basename(xml)[:-4]] = root
    return {k: xml_roots[k] for k in sorted(xml_roots)}


def test_extract_lines(xml_roots):
    lines = xmle.extract_lines(xml_roots["small_xml_example_1"])

    assert len(lines) == 3
    assert lines[0] == "Test line 1"


def test_extract_lines_text_region_order():
    four_region_xml = ET.parse("tests\\4_TextRegion_xml_example.xml")
    four_region_root = four_region_xml.getroot()
    ordered_lines = xmle.extract_lines(four_region_root)

    assert ordered_lines[0] == "Test line 1"
    assert ordered_lines[3] == "Test line 4"


def test_extract_lines_for_vol(xml_roots):
    all_lines, xml_track_df = xmle.extract_lines_for_vol(xml_roots)

    assert len(all_lines) == 6
    assert all_lines[-1] == "Test line 6"

    assert xml_track_df.shape == (6, 2)  # must be same length as all_lines
    assert xml_track_df['xml'].tolist() == [
        "small_xml_example_1", "small_xml_example_1", "small_xml_example_1",
        "small_xml_example_2", "small_xml_example_2", "small_xml_example_2"
    ]


def test_check_line():
    i_num_check = xmle.shelfmark_check("IA. 33")
    c_num_check = xmle.shelfmark_check("C.44")
    bad_check = xmle.shelfmark_check("asdf")

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


# separate so easier to see their values in tests
fix_in_xml = ET.parse("tests\\title_xml_example.xml")
fix_root = fix_in_xml.getroot()
fix_lines = xmle.extract_lines(fix_root)
fix_titles, fix_title_indices = ["IA. 123TITLE1456", "IA. 789SECONDTITLE1506"], [[0, 1, 2], [6, 7, 8]]# xmle.find_headings(fix_lines)

@pytest.fixture()
def lines():
    return fix_lines

@pytest.fixture()
def titles():
    return fix_titles

@pytest.fixture()
def indices():
    return fix_title_indices


def test_find_headings(xml_roots, lines, titles, indices):
    t, i = xmle.find_headings(["asdf"])
    assert not t
    assert not i

    no_title_lines, xml_track_df = xmle.extract_lines_for_vol(xml_roots)
    no_titles, no_all_title_indices = xmle.find_headings(no_title_lines)
    # should both be empty
    assert not no_titles
    assert not no_all_title_indices

    """"
    the xml used to make title_indices contains three IA. numbers that could start titles
    The second IA. (IA. 456) has its title interrupted by IA. 789 before a date is found
    This tests the 
    `if shelfmark_check(title_part):
    `    break
    section of find_headings 
    """

    titles, indices = xmle.find_headings(lines)

    assert len(titles), len(indices) == (2, 2)
    assert titles == ["IA. 123TITLE1456", "IA. 789SECONDTITLE1506"]
    assert indices == [[0, 1, 2], [6, 7, 8]]


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


def test_gen_title_refs(lines, indices):
    title_refs = xmle.gen_title_refs(lines, indices)

    assert len(title_refs) == 2
    assert title_refs == ["IA. 123TI", "IA. 789SE"]


def test_generate_xml():
    in_xml = ET.parse("tests\\title_xml_example.xml")
    root = in_xml.getroot()
    all_lines = xmle.extract_lines(root)
    title, all_title_indices = xmle.find_headings(all_lines)

    # out_xml = xmle.generateXML(all_title_indices, all_lines, )


def test_extract_catalogue_entries(lines, indices):
    root = ET.parse("tests\\title_xml_example.xml").getroot()
    _, xml_track_df = xmle.extract_lines_for_vol({"title_xml_example": root})
    lines += ["", "IA. 666", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
    indices += [[10, 11, 12], [14, 15, 16]]  # need an extra pair due to [:-2] indexing in save_raw_txt
    title_refs = xmle.gen_title_refs(lines, indices)

    catalogue_entries = xmle.extract_catalogue_entries(lines, indices, title_refs, xml_track_df)

    assert catalogue_entries.shape == (2,2)
    assert catalogue_entries["labels"].tolist() == ["title_xml_example_IA_123", "title_xml_example_IA_789SE"]


def test_save_raw_txt(tmp_path, lines, titles, indices):
    root = ET.parse("tests\\title_xml_example.xml").getroot()
    _, xml_track_df = xmle.extract_lines_for_vol({"title_xml_example": root})
    lines, indices = lines, indices
    lines += ["", "IA. 666", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
    indices += [[10, 11, 12], [14, 15, 16]]  # need an extra pair due to [:-2] indexing in save_raw_txt
    title_refs = xmle.gen_title_refs(lines, indices)
    out_path = tmp_path

    xmle.save_raw_txt(lines, indices, title_refs, xml_track_df, out_path)

    filepath_1 = tmp_path.joinpath(f"{xml_track_df.iloc[0, 0]}_IA_789SE.txt")
    filepath_2 = tmp_path.joinpath(f"{xml_track_df.iloc[0,0]}_IA_666.txt")

    assert len(indices) == 4
    assert os.path.exists(filepath_1)
    assert os.path.exists(filepath_2)

    with open(filepath_1) as f:
        saved_lines = f.readlines()

    assert len(saved_lines) == 5
    assert saved_lines[0] == "TITLE\n"
    assert saved_lines[-1] == "TITLE\n"
