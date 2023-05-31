import os
import sys
import glob
from xml.etree import ElementTree as ET
from tqdm import tqdm
from src.data import xml_extraction as xmle

if __name__ == '__main__':
    page_xmls = []
    network_loc = "\\\\ad\\collections\\TwoCenturies\\TwoCenturies IV\\Incunabula"
    suffix = "column pages Transkribus export"

    for i in range(8, 9):
        page_xmls.append(
            [
                os.path.join(network_loc, f"BMC_{i + 1} 2 {suffix}"),
                os.path.join(network_loc, f"BMC_{i + 1} 4 {suffix}")
            ]
        )

    # this one didn't work for some reason
    # 'BMC_5 2 column pages Transkribus export'

    for x in page_xmls:
        page_xml_loc_2 = os.path.join(x[0], r"*\*\page\*.xml")
        page_xml_loc_4 = os.path.join(x[1], r"*\*\page\*.xml")
        out_path = os.path.join(network_loc, "split_data\\test", os.path.basename(x[0]).split(" ")[0])
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

        print(f"\nGetting xml roots from {os.path.dirname(page_xml_loc_2)}  {os.path.basename(page_xml_loc_2)}/{os.path.basename(page_xml_loc_4)}")
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
        allLines, xml_track_df = xmle.extract_lines_for_vol(current_volume)
        allLines = [line for line in allLines if line is not None]
        xml_track_df = xml_track_df.dropna(subset="line")
        titles, all_title_indices = xmle.find_headings(allLines)
        title_refs = xmle.gen_title_refs(all_title_indices, allLines)

        print(f"\nSaving catalogue entries to {out_path}\n")
        if not os.path.exists(out_path):
            os.makedirs(out_path)

        xmle.save_poorly_scanned_pages(xmle.get_poorly_scanned_pages(current_volume, xmls), out_path)
        print("Saving raw txt files")
        xmle.save_raw_txt(all_title_indices, allLines, xml_track_df, os.path.join(out_path, "rawtextfiles"), title_refs)
        # print("Saving split txt files")
        # xmle.saveSplitTxt(allTitleIndices, allLines, os.path.join(out_path, "splittextfiles"), titleRefs)
        xmle.save_xml(all_title_indices, allLines, out_path, title_refs)

        # xmle.saveAll(
        #     currentVolume=currentVolume,
        #     xmls=xmls,
        #     xml_track_df=xml_track_df,
        #     allTitleIndices=allTitleIndices,
        #     allLines=allLines,
        #     path=out_path,
        #     titleRefs=titleRefs
        # )
