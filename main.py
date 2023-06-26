import os
import glob
from xml.etree import ElementTree as ET
from tqdm import tqdm
from src.data import xml_extraction as xmle

if __name__ == '__main__':
    page_xmls = []
    network_loc = "\\\\ad\\collections\\TwoCenturies\\TwoCenturies IV\\Incunabula"
    suffix = "column pages Transkribus export"

    for i in range(1, 11):
        page_xmls.append(
            [
                os.path.join(network_loc, f"BMC_{i} 2 {suffix}"),
                os.path.join(network_loc, f"BMC_{i} 4 {suffix}")
            ]
        )

    # this one didn't work for some reason
    # 'BMC_5 2 column pages Transkribus export'

    for x in page_xmls:

        out_path = os.path.join(
            network_loc,
            "split_data",
            os.path.basename(x[0]).split(" ")[0]
        )

        page_xml_loc_2 = os.path.join(x[0], r"*\*\page\*.xml")
        page_xml_loc_4 = os.path.join(x[1], r"*\*\page\*.xml")
        attempts = 0
        while attempts < 3:
            xmls_2 = glob.glob(os.fsencode(page_xml_loc_2))
            xmls_4 = glob.glob(os.fsencode(page_xml_loc_4))

            if xmls_2 and xmls_4:
                xmls = xmls_2 + xmls_4
                n_cols = [2 for x in xmls_2] + [4 for x in xmls_4]
                break
            else:
                attempts += 1
                continue
        else:
            raise IOError(f"Failed to connect to {os.path.dirname(page_xml_loc_2)}  {os.path.basename(page_xml_loc_2)}/{os.path.basename(page_xml_loc_4)}")

        xmlroots = {}

        print(f"\nGetting xml roots from {page_xml_loc_2.replace(' 2 ',' [2, 4] ')}")
        for file, n_col in tqdm(zip(xmls, n_cols), total=len(xmls)):
            file_name = os.fsdecode(file)
            attempts = 0
            while attempts < 3:
                try:
                    tree = ET.parse(file_name)
                    break
                except FileNotFoundError:
                    attempts += 1
                    continue
            else:
                raise FileNotFoundError(f"Failed to connect to: {file_name}")
            root = tree.getroot()
            xmlroots[os.path.basename(file_name)[5:-4] + f"_{n_col}"] = root  # take the label that spans different sections of a volume

        print("\nExtrating catalogue entries from xmls")
        current_volume = {k: xmlroots[k] for k in sorted(xmlroots)}
        lines, xml_track_df = xmle.extract_lines_for_vol(current_volume)
        title_shelfmarks, title_indices = xmle.find_headings(lines)
        entry_df = xmle.extract_catalogue_entries(lines, title_indices, title_shelfmarks, xml_track_df)
        print(f"Extracted {len(entry_df)} entries")

        # fname = r"\\ad\collections\TwoCenturies\TwoCenturies IV\Incunabula\split_data\test\BMC_9_gen_title_refs_refactor\catalogue_entries.csv"
        # entry_df = pd.read_csv(fname, converters={"entry": lambda x: x[2:-2].split("\', \'")})

        print(f"Saving catalogue entries to {out_path}")
        if not os.path.exists(out_path):
            os.makedirs(out_path)

        entry_df.to_csv(os.path.join(out_path, "catalogue_entries_leading_caps.csv"), index=False)
        # xmle.save_poorly_scanned_pages(xmle.get_poorly_scanned_pages(current_volume, xmls), out_path)
        # print("Saving raw txt files")
        # # entry_df.groupby(by=["xml", "shelfmark"]).progress_apply(lambda x: xmle.groupby_save(x, outpath))
        # # print("Saving split txt files")
        # # xmle.saveSplitTxt(allTitleIndices, allLines, os.path.join(out_path, "splittextfiles"), titleRefs)
        # xmle.save_xml(lines, title_indices, title_shelfmarks, out_path)