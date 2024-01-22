import src.data.xml_extraction as xmle
from xml.etree import ElementTree as ET
import os
import glob
import pdb
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


def test_gen_2_4_col_xml_paths():
    xmls = xmle.gen_2_4_col_xml_paths("tests\\BMC_3_2", "tests\\BMC_3_4")
    assert xmls[0] == ["tests\\BMC_3_2\\J_2704_aa_30_3_0052.pxml"]
    assert xmls[1] == ["tests\\BMC_3_4\\J_2704_aa_30_3_0053.pxml"]


def test_gen_2_4_col_xml_trees():
    xml_2 = ["tests\\BMC_3_2\\J_2704_aa_30_3_0052.pxml"]
    xml_4 = ["tests\\BMC_3_4\\J_2704_aa_30_3_0053.pxml"]
    roots = xmle.gen_2_4_col_xml_trees(xml_2, xml_4)
    assert len(roots) == 2
    assert list(roots.keys()) == ["J_2704_aa_30_3_0052_2", "J_2704_aa_30_3_0053_4"]
    assert type(roots["J_2704_aa_30_3_0052_2"]) == ET.Element


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


def test_find_shelfmark():
    ia_sm = xmle.find_shelfmark("IA. 33.")
    ic_sm = xmle.find_shelfmark("IC. 3. a. 4.")
    i_letter_sm = xmle.find_shelfmark("IC. a3.")
    preceding_letter_i_sm = xmle.find_shelfmark("ASDFIB. 1345.")

    c_brackets_sm = xmle.find_shelfmark("(C.44.)")
    c_space_sm = xmle.find_shelfmark(" C. 15632. ")
    preceding_letter_c_sm = xmle.find_shelfmark("aC. 15632.")

    bad_lower = xmle.find_shelfmark("asdf")
    bad_caps = xmle.find_shelfmark("NOTHINGTOSEEHERE")

    assert ia_sm == "IA. 33"
    assert ic_sm == "IC. 3. a. 4"
    assert i_letter_sm == "IC. a3"
    assert preceding_letter_i_sm is None

    assert c_brackets_sm == "C.44"
    assert c_space_sm == "C. 15632"
    assert preceding_letter_c_sm is None

    assert not bad_lower
    assert not bad_caps

def test_date_check():
    date_check = xmle.date_check("1409")
    untitled_check = xmle.date_check("Undated")
    bad_check = xmle.date_check("0300")

    assert date_check
    assert untitled_check
    assert not bad_check


# def test_get_i_num_title():
#     i_num = xmle.get_i_num_title("IA.123456aaa")
#     i_num_2_fullstop = xmle.get_i_num_title("IA.123.wrong.answer")
#
#     assert i_num == "IA.123456"
#     assert i_num_2_fullstop == "IA.123"
#
#
# def test_get_g_num_title():
#     g_num = xmle.get_i_num_title("G.123456aaa")
#     g_num_2_fullstop = xmle.get_i_num_title("G.123.wrong.answer")
#
#     assert g_num == "G.123456"
#     assert g_num_2_fullstop == "G.123"
#
#
# def test_get_c_num_title():
#     c_num = xmle.get_c_num_title("C.123456aaa")
#     c_num_4_fullstop = xmle.get_c_num_title("C.12.3.more.shelfmark.here")
#
#     assert c_num == "C.123456aa"
#     assert c_num_4_fullstop == "C.12.3.more"



# separate so easier to see their values in tests
fix_in_xml = ET.parse("tests\\title_xml_example.xml")
fix_root = fix_in_xml.getroot()
fix_lines = xmle.extract_lines(fix_root)
fix_titles, fix_title_indices = ["IA. 123.TITLE1456", "IA. 789.SECONDTITLE1506"], [[0, 1, 2], [6, 7, 8]]

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

    # lines is produced from title_xml_example.xml rather than the small_xml_examples
    title_shelfmarks, indices = xmle.find_headings(lines)

    assert len(title_shelfmarks), len(indices) == (2, 2)
    assert title_shelfmarks == ["IA. 123TI", "IA. 789SE"]
    assert indices == [[0, 1, 2], [6, 7, 8]]


def test_extract_catalogue_entries(lines, indices):
    root = ET.parse("tests\\title_xml_example.xml").getroot()
    lines, xml_track_df = xmle.extract_lines_for_vol({"title_xml_example": root})
    title_shelfmarks, _ = xmle.find_headings(lines)
    catalogue_entries = xmle.extract_catalogue_entries(lines, indices, title_shelfmarks, xml_track_df)

    assert catalogue_entries.shape == (2, 6)
    assert catalogue_entries.columns.tolist() == ["xml", "vol_entry_num", "shelfmark", "entry", "title", "entry_text"]  # "copy"
    assert catalogue_entries["xml"].tolist() == ["title_xml_example", "title_xml_example"]
    assert catalogue_entries["shelfmark"].tolist() == ["IA. 789SE", "IA. 353"]
    # assert catalogue_entries["copy"].sum() == catalogue_entries.shape[0]
    assert catalogue_entries["entry"].transform(len).tolist() == [6, 3]
    assert catalogue_entries.loc[0, "entry"][0] == "TITLE"
    assert catalogue_entries.loc[0, "entry"][-1] == "IA. 789"
    assert catalogue_entries.loc[1, "entry"][0] == "SECONDTITLE"
    assert catalogue_entries.loc[1, "entry"][-1] == "IA. 353"


def test_generate_xml(): # TODO update once generate_xml has been updated
    in_xml = ET.parse("tests\\title_xml_example.xml")
    root = in_xml.getroot()
    all_lines = xmle.extract_lines(root)
    title, all_title_indices = xmle.find_headings(all_lines)

    # out_xml = xmle.generate_xml(all_title_indices, all_lines, )

"""
Obsolete as now using df groupby/apply
def test_save_raw_txt(tmp_path, lines, titles, indices):
    root = ET.parse("tests\\title_xml_example.xml").getroot()
    _, xml_track_df = xmle.extract_lines_for_vol({"title_xml_example": root})
    lines, indices = lines, indices
    title_shelfmarks, _ = xmle.find_headings(lines)
    title_shelfmarks += ["IA. 353"]
    print(title_shelfmarks)
    lines += ["", "IA. 666", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
    indices += [[10, 11, 12]]  # need an extra set due to [:-1] indexing in save_raw_txt
    out_path = tmp_path

    xmle.save_raw_txt(lines, indices, title_shelfmarks, xml_track_df, out_path)

    filepath_1 = tmp_path.joinpath(f"{xml_track_df.iloc[0, 0]}_IA_789SE.txt")
    filepath_2 = tmp_path.joinpath(f"{xml_track_df.iloc[0,0]}_IA_353.txt")

    assert os.path.exists(filepath_1)
    assert os.path.exists(filepath_2)

    with open(filepath_1) as f:
        saved_lines = f.readlines()

    assert len(saved_lines) == 5
    assert saved_lines[0] == "TITLE\n"
    assert saved_lines[-1] == "TITLE\n"
"""
