import os
import re
import xml
from xml.dom import minidom
import numpy as np
import pandas as pd
from langdetect import detect
from tqdm import tqdm


# Extracts all lines for given xmltree
def extract_lines(root: xml.etree.ElementTree.Element):
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
def extract_lines_for_vol(vol: dict[str: xml.etree.ElementTree.Element]):
    all_lines = []
    xml_idx = []
    for xml, root in tqdm(vol.items()):
        root_lines = extract_lines(root)
        all_lines += root_lines
        xml_idx += [xml] * len(root_lines)
    xml_track_df = pd.DataFrame(
        data={
            "xml": xml_idx,
            "line": all_lines
        }
    )
    return all_lines, xml_track_df


# Regular expressions used in the detection og headings
caps_regex = re.compile("[A-Z][A-Z][A-Z]+")
c_num_regex = re.compile("C\.[0-9]")  # C number title references
i_num_regex = re.compile("I[ABC]\.\s[0-9]")  # I number title references
date_regex = re.compile("1[45][0-9][0-9]")  # Date format regexes (specific to this volume)


# Looks for identifying marks of a catalogue heading beginning
def check_line(line: str):
    if line is not None:
        return i_num_regex.search(line) or c_num_regex.search(line)
    else:
        return False


# Looks for identifying marks of a catalogue heading ending
def date_check(title_part: str):
    return date_regex.search(title_part) or "Undated" in title_part


# NOT USED RIGHT NOW
def get_init_title(lines: list[str]):
    output = ""
    title = False
    for line in lines[:5]:
        output += line
        if date_check(line):
            title = True
            break
    if title and len(caps_regex.findall(output)) > 0:
        return output
    else:
        return " ".join(caps_regex.findall("".join(lines[:5])))


# Finds all headings from a list of lines
def find_headings(all_lines: list[str]):
    titles = []  # The names of the titles
    index = -1
    all_title_indices = []
    for x in range(len(all_lines)):
        index += 1
        line = all_lines[x]
        if line is not None:
            if check_line(line):  # If start of chapter found
                output = line
                end_found = False
                title_indices = [index]
                for y in range(1, 7):
                    try:
                        title_part = all_lines[x + y]
                    except:
                        pass
                    if check_line(title_part):  # If a new chapter begins during the current title
                        break
                    output += title_part
                    title_indices.append(index + y)
                    if date_check(title_part):  # If end of a chapter found
                        end_found = True
                        break

                if end_found and len(caps_regex.findall(output)) > 0:  # Title has to contain all uppercase words
                    titles.append(output)
                    all_title_indices.append(title_indices)

    return titles, all_title_indices


# Extracts the title reference number from a line for I numbers (e.g. IB929)
def get_i_num_title(full_title: str):
    if full_title[:14].count(".") >= 2:
        return ".".join(full_title.split(".")[:2])
    else:
        return full_title[:9]


# Extracts the title reference number from a line for C numbers (only found in 1 volume)
def get_c_num_title(full_title: str):
    if full_title[:14].count(".") >= 4:
        return ".".join(full_title.split(".")[:4])
    else:
        return full_title[:10]


# Finds the associated title reference from a given line
def find_title_ref(full_title: str):
    if i_num_regex.search(full_title) is not None:
        ref = get_i_num_title(full_title[i_num_regex.search(full_title).start():])
        return ref.replace("/", ".")
    elif c_num_regex.search(full_title) is not None:
        ref = get_c_num_title(full_title[c_num_regex.search(full_title).start():])
        return ref.replace("/", ".")
    else:
        print("Unrecognized title format")


def gen_title_refs(all_title_indices: list[list[int]], all_lines: list[str]):

    title_refs = []

    for itr in range(len(all_title_indices[:-1])):
        title_indices = all_title_indices[itr]
        full_title = "".join([all_lines[x] for x in title_indices])
        title_ref = find_title_ref(full_title)
        title_refs.append(title_ref)

    return title_refs


# Generates an XML document based on the found catalogue headings in the document
def generate_xml(all_title_indices: list[list[int]], all_lines: list[str], title_refs):
    xml = minidom.Document()
    text = xml.createElement('text')

    for itr in range(len(all_title_indices[:-2])):
        title_indices = all_title_indices[itr]
        catalogue_indices = [x for x in range(title_indices[-1], all_title_indices[itr + 1][0])]
        full_title = "".join([all_lines[x] for x in title_indices])

        chapter = xml.createElement('chapter')
        chapter.setAttribute("REFERENCE", title_refs[itr + 1])
        chapter.setAttribute("HEADING", full_title)

        for catalogue_index in catalogue_indices:
            line = xml.createElement('line')
            line.setAttribute("CONTENT", all_lines[catalogue_index])
            chapter.appendChild(line)

        text.appendChild(chapter)

    xml.appendChild(text)
    return xml


# Saves the generated XML for the headings into a chosen location
def save_xml(all_title_indices, all_lines, out_path, title_refs):
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    xml = generate_xml(all_title_indices, all_lines, title_refs)
    xml_str = xml.toprettyxml(indent="\t")
    save_path_file = out_path + "/headings.xml"
    with open(save_path_file, "w", encoding="utf-8") as f:
        f.write(xml_str)
        f.close()


# Saves all of the text, split by chapters, into text files
def save_raw_txt(all_title_indices, all_lines, xml_track_df, out_path, title_refs):
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    for itr in tqdm(range(len(all_title_indices[:-2]))):
        title_indices = all_title_indices[itr]
        catalogue_indices = [x for x in range(title_indices[1], all_title_indices[itr + 1][0])]

        xml = xml_track_df.loc[title_indices[1], "xml"]
        clean_shelfmark = title_refs[itr + 1].replace(".", "_").replace(" ", "")
        save_path_file = os.path.join(out_path, f"{xml}_{clean_shelfmark}.txt")

        with open(save_path_file, "w", encoding="utf-8") as f:
            for line_index in catalogue_indices:
                f.write(all_lines[line_index] + "\n")


# Splits up a document by the detected language
def split_by_language(lines):
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


# Saves all of the text, split by chapters into text files where non-english sections of text are removed
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


# Saves the raw text files, the text files split by language and the XML files
def save_all(current_volume, xmls, xml_track_df, all_title_indices, all_lines, path, title_refs):
    out_path = path
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    save_poorly_scanned_pages(get_poorly_scanned_pages(current_volume, xmls), out_path)
    print("Saving raw txt files")
    save_raw_txt(all_title_indices, all_lines, xml_track_df, os.path.join(out_path, "rawtextfiles"), title_refs)
    print("Saving split txt files")
    save_split_txt(all_title_indices, all_lines, os.path.join(out_path, "splittextfiles"), title_refs)
    save_xml(all_title_indices, all_lines, out_path, title_refs)
