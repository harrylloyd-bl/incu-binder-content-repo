import os
import re
from xml.dom import minidom
import numpy as np
import pandas as pd
from langdetect import detect
from tqdm import tqdm
from xml.etree import ElementTree as ET


# Extracts all lines for given xmltree
def extract_lines(root: ET.Element) -> list[str]:
    """
    Extract the text lines from a page xml
    :param root: ET.Element: an xml root
    :return: list[str]: a list of the text lines in the xml
    """
    lines = []

    text_regions = [x for x in root[1] if len(x) > 2]  # Empty Text Regions Removed

    if len(text_regions) % 2 == 0:
        half = int(len(text_regions) / 2)
        new_text_regions = []
        for x in range(half):
            new_text_regions.append(text_regions[x])
            new_text_regions.append(text_regions[x + half])
        text_regions = new_text_regions

    for text_region in text_regions:
        text_lines = text_region[1:-1]  # Skip coordinate data in first child
        for text_line in text_lines:
            lines.append(text_line[-1][0].text)  # Text equivalent for line
    return lines


# Extracts lines for a collection of xmltrees
def extract_lines_for_vol(vol: dict[str: ET.Element]) -> tuple[list[str], pd.DataFrame]:
    lines = []
    xml_idx = []
    for xml, root in tqdm(vol.items()):
        root_lines = extract_lines(root)
        lines += root_lines
        xml_idx += [xml] * len(root_lines)
    xml_track_df = pd.DataFrame(
        data={
            "xml": xml_idx,
            "line": lines
        }
    )
    return lines, xml_track_df


# Regular expressions used to detect headings
caps_regex = re.compile("[A-Z][A-Z][A-Z]+")
c_num_regex = re.compile("C\\.[0-9]")  # C number title references
i_num_regex = re.compile("I[ABC]\\.\\s[0-9]")  # I number title references
date_regex = re.compile("1[45][0-9][0-9]")


def shelfmark_check(line: str) -> re.Match[str] | None | bool:
    """
    Looks for identifying marks of a catalogue heading beginning
    :param line:
    :return:
    """
    if line:
        return i_num_regex.search(line) or c_num_regex.search(line)
    else:
        return False


def date_check(line: str) -> re.Match | str | None:
    """
    Looks for identifying marks of a catalogue heading ending
    :param line:
    :return:
    """
    if line:
        return date_regex.search(line) or "Undated" in line
    else:
        return False


def get_i_num_title(full_title: str) -> str:
    """
    Extracts the title reference number from a line for I numbers (e.g. IB929)
    :param full_title:
    :return:
    """
    if full_title[:14].count(".") >= 2:
        return ".".join(full_title.split(".")[:2])
    else:
        return full_title[:9]


def get_c_num_title(full_title: str) -> str:
    """
    Extracts the title reference number from a line for C numbers (only found in 1 volume)
    :param full_title:
    :return:
    """
    if full_title[:14].count(".") >= 4:
        return ".".join(full_title.split(".")[:4])
    else:
        return full_title[:10]


def find_title_shelfmark(title: str) -> str:
    """
    Finds the associated title reference from a given line
    :param title:
    :return:
    """
    if i_num_regex.search(title) is not None:
        ref = get_i_num_title(title[i_num_regex.search(title).start():])
        return ref.replace("/", ".")
    elif c_num_regex.search(title) is not None:
        ref = get_c_num_title(title[c_num_regex.search(title).start():])
        return ref.replace("/", ".")
    else:
        print("Unrecognized title format")


# Finds all headings from a list of lines
def find_headings(lines: list[str]) -> tuple[list[str], list[list[int]]]:
    titles = []  # The names of the titles
    title_indices = []

    # TODO include the first catalogue entry as well
    for i, l in enumerate(lines):
        if shelfmark_check(l):
            title = l
            title_index = [i]
            j = 1
            while i + j < len(lines) and j < 8:
                title_part = lines[i + j]
                if shelfmark_check(title_part):  # If a new catalogue entry begins during the current title
                    j = 1
                    break

                title += title_part
                title_index.append(i + j)
                j += 1

                if date_check(title_part) and caps_regex.findall(title):  # Date marks the end of a heading
                    titles.append(title)
                    title_indices.append(title_index)
                    j = 1
                    break

    title_shelfmarks = [find_title_shelfmark(t) for t in titles]

    return title_shelfmarks, title_indices


def extract_catalogue_entries(lines: list[str],
                              title_indices: list[list[int]],
                              title_shelfmarks: list[str],
                              xml_track_df: pd.DataFrame) -> pd.DataFrame:
    """
    Use catalogue entry indices to extract from the main list of lines
    :param lines:
    :param title_indices:
    :param title_shelfmarks:
    :param xml_track_df:
    :return:
    """
    xmls = []
    shelfmarks = []
    entries = []

    for i, idx in tqdm(enumerate(title_indices[:-1]), total=len(title_indices) - 1):
        # take the 1 position in idx and title_indices[i+1] as that's excludes the leading shelfmark and includes the trailing shelfmark
        # TODO fix this indexing for the first entry?
        entry = lines[idx[1]: title_indices[i + 1][1]]
        entries.append(entry)

        xmls.append(xml_track_df.loc[idx[1], "xml"])
        shelfmarks.append(title_shelfmarks[i + 1])

    last_entry = lines[title_indices[-1][1]: len(lines)]
    entries.append(last_entry)
    xmls.append(xml_track_df.loc[title_indices[-1][1], "xml"])
    shelfmarks.append(find_title_shelfmark("".join(last_entry)))

    entry_df = pd.DataFrame(
        data={"xml": xmls, "shelfmark": shelfmarks, "copy": 1,
              "entry": entries, "title": title_indices}
    )

    return entry_df


def extract_another_copy():
    pass


# use this for the saving fn to create os friendly file names with shelfmark
# .replace(".", "_").replace(" ", "")

# Saves all of the text, split into catalogue entries, into text files
def save_raw_txt(lines: list[str],
                 title_indices: list[list[int]],
                 title_shelfmarks: list[str],
                 xml_track_df: pd.DataFrame,
                 out_path: str | os.PathLike) -> None:

    if not os.path.exists(out_path):
        os.makedirs(out_path)

    for i, idx in tqdm(enumerate(title_indices[:-1]), total=len(title_indices) - 1):
        catalogue_indices = [x for x in range(idx[1], title_indices[i + 1][0])]

        source_xml = xml_track_df.loc[idx[1], "xml"]
        clean_shelfmark = title_shelfmarks[i + 1].replace(".", "_").replace(" ", "")
        save_path_file = os.path.join(out_path, f"{source_xml}_{clean_shelfmark}.txt")

        with open(save_path_file, "w", encoding="utf-8") as f:
            for line_index in catalogue_indices:
                f.write(lines[line_index] + "\n")

    return None


# Splits up a document by the detected language
def split_by_language(lines: list[str]):
    split_lines = []
    first_line_lan = ""
    second_line_lan = ""
    try:
        first_line_lan = detect(lines[0])
    except:
        first_line_lan = "can't find language"
    try:
        second_line_lan = detect(lines[1])
    except:
        second_line_lan = "can't find language"
    first2_lines = [first_line_lan, second_line_lan]
    language_en = first2_lines.count("en") == 2
    first_language = language_en
    current_block = [lines[0], lines[1]]
    for ind in range(2, len(lines[:-1])):
        c_line_lan = ""
        n_line_lan = ""
        try:
            c_line_lan = detect(lines[ind])
        except:
            c_line_lan = "can't find language"
        try:
            n_line_lan = detect(lines[ind + 1])
        except:
            n_line_lan = "can't find language"
        next2_lines = [c_line_lan, n_line_lan]
        if (next2_lines.count("en") == 0) and language_en:
            language_en = False
            split_lines.append(current_block)
            current_block = [lines[ind]]
        elif (next2_lines.count("en") == 2) and (not language_en):
            language_en = True
            split_lines.append(current_block)
            current_block = [lines[ind]]
        else:
            current_block.append(lines[ind])
    current_block.append(lines[-1])
    split_lines.append(current_block)
    return first_language, split_lines


# Saves all of the text, split into catalogue entries into text files where non-english sections of text are removed
def save_split_txt(all_title_indices, all_lines, out_path, title_refs):
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    for itr in tqdm(range(len(all_title_indices[:-2]))):
        title_indices = all_title_indices[itr]
        catalogue_indices = [x for x in range(title_indices[1], all_title_indices[itr + 1][0])]
        full_title = "".join([all_lines[x] for x in title_indices])

        catalogue_lines = [all_lines[x] for x in catalogue_indices]
        first_language, split_catalogue_lines = split_by_language(catalogue_lines)

        save_path_file = os.path.join(out_path, title_refs[itr + 1].replace(".", "-") + ".txt")
        with open(save_path_file, "w", encoding="utf-8") as f:
            f.write(full_title + "\n")
            language_en = first_language
            for block_lines in split_catalogue_lines:
                if language_en:
                    for line in block_lines:
                        f.write(line + "\n")
                else:
                    f.write("-----------------------------------\n")
                    f.write("NON-ENGLISH SECTION LASTING {} LINES\n".format(len(block_lines)))
                    f.write("-----------------------------------\n")
                language_en = not language_en


# Returns the number of lines in a page which are too long
def num_outliers_for_page(lines, std, mean, threshold=2):
    lengths = [len(x.split()) for x in lines if x is not None]
    lengths = [(x - mean) for x in lengths]
    lengths = [(x / std) for x in lengths]
    num_outliers = len([x for x in lengths if x > threshold])
    return num_outliers


# Find all of the poorly scanned pages in the input
def get_poorly_scanned_pages(volume_root, file_names):
    poorly_scanned_page_nums = []

    # Get all the lines for the volume and find the mean and std for the line lengths across all volumes
    vol_lines, xml_check_df = extract_lines_for_vol(volume_root)
    lengths = [len(x.split()) for x in vol_lines if x is not None]
    mean = np.mean(lengths)
    std = np.std(lengths)

    # For every page (xmlroot) in the volume
    for root, filename in zip(volume_root.values(), file_names):
        page = root
        page_lines = extract_lines(page)
        num_outliers = num_outliers_for_page(page_lines, std, mean)
        if num_outliers > 5:
            poorly_scanned_page_nums.append(filename.decode("utf-8"))
    return poorly_scanned_page_nums


# Save poorly scanned page numbers to a text file
def save_poorly_scanned_pages(poorly_scanned, out_path):
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    save_path_file = os.path.join(out_path, "poorlyscanned.txt")
    with open(save_path_file, "w", encoding="utf-8") as f:
        for scan in poorly_scanned:
            f.write(scan + "\n")


def generate_xml(lines: list[str],
                 title_indices: list[list[int]],
                 title_refs: list[str]) -> minidom.Document:
    """
    Generates an XML document based on the found catalogue headings in the document
    :param lines:
    :param title_indices:
    :param title_refs:
    :return:
    """
    xml = minidom.Document()
    text = xml.createElement('text')

    for i, idx in tqdm(enumerate(title_indices[:-1]), total=len(title_indices) - 1):
        catalogue_indices = [x for x in range(idx[1], title_indices[i + 1][0])]
        full_title = "".join([lines[x] for x in idx])

        catalogue_entry = xml.createElement('catalogue_entry')
        catalogue_entry.setAttribute("SHELFMARK", title_refs[i + 1])
        catalogue_entry.setAttribute("HEADING", full_title)

        for catalogue_index in catalogue_indices:
            line = xml.createElement('line')
            line.setAttribute("CONTENT", lines[catalogue_index])
            catalogue_entry.appendChild(line)

        text.appendChild(catalogue_entry)

    xml.appendChild(text)
    return xml


# Saves the generated XML for the headings into a chosen location
def save_xml(lines: list[str],
             title_indices: list[list[int]],
             title_refs: list[str],
             out_path: str | os.PathLike) -> None:

    if not os.path.exists(out_path):
        os.makedirs(out_path)

    xml = generate_xml(lines, title_indices, title_refs)
    xml_str = xml.toprettyxml(indent="\t")
    save_path_file = out_path + "/headings.xml"
    with open(save_path_file, "w", encoding="utf-8") as f:
        f.write(xml_str)
        f.close()

    return None


# I prefer manually doing each step in main
# Saves the raw text files, the text files split by language and the XML files
def save_all(current_volume, xmls, xml_track_df, all_title_indices, all_lines, path, title_refs):
    out_path = path
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    save_poorly_scanned_pages(get_poorly_scanned_pages(current_volume, xmls), out_path)
    print("Saving raw txt files")
    save_raw_txt(all_lines, all_title_indices, title_refs, xml_track_df, os.path.join(out_path, "rawtextfiles"))
    print("Saving split txt files")
    save_split_txt(all_title_indices, all_lines, os.path.join(out_path, "splittextfiles"), title_refs)
    save_xml(all_lines, all_title_indices, title_refs, out_path)


# made obsolete by inclusion in find_headings
def gen_title_refs(lines: list[str], title_indices: list[list[int]]) -> list[str]:
    """
    Extracts full titles from the list of all lines
    For each full title extracts the title reference
    :param title_indices: list[list[int]]: Indices for all the lines in lines that constitute a title
    :param lines: A set of Incunabula lines, e.g. from a full volume or a single page
    :return: list[str]
    """
    title_refs = []

    for idx in title_indices:
        full_title = "".join([lines[x] for x in idx])
        title_ref = find_title_shelfmark(full_title)
        title_refs.append(title_ref)

    return title_refs