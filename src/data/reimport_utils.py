import re

def reconstruct_word_coords(s):
    line_re = re.compile(r"\[\[.*?\]\]")
    word_re = re.compile(r"\[.*?\]")
    num_re = re.compile(r"[\d]*")
    raw_lines = line_re.findall(s[1:-1])
    split_word_lines = [word_re.findall(l[1:-1]) for l in raw_lines]
    lines = []
    for sw_line in split_word_lines:
        line = [[int(x) for x in num_re.findall(word) if x] for word in sw_line]
        lines.append(line)
    return lines


def reconstruct_en_entry(s):
    return " ".join(s[2:-2].split("', '"))


def reconstruct_xmls(s):
    return s[1:-1].replace(" ", "").replace("'", "").split(",")


def reconstruct_xml_start_line(s):
    return [int(loc) for loc in s[1:-1].replace(" ", "").split(",")]


converters = {"word_locations": reconstruct_word_coords, "en_only": reconstruct_en_entry, "xmls": reconstruct_xmls,
              "xml_start_line": reconstruct_xml_start_line}
