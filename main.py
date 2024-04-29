import os
from src.data import xml_extraction as xmle

if __name__ == '__main__':

    for i in range(3, 4):
        two_col_loc = f"data\\raw\\BMC_{i}_2\\*\\*.pxml"
        four_col_loc = f"data\\raw\\BMC_{i}_4\\*\\*.pxml"
        xmls_2, xmls_4 = xmle.gen_xml_paths(two_col_loc), xmle.gen_xml_paths(four_col_loc)
        print(f"{len(xmls_2) + len(xmls_4)} xmls extracted from\n"
              f"2 col ({len(xmls_2):03}): {os.path.dirname(xmls_2[0])}\n4 col ({len(xmls_4):03}): {os.path.dirname(xmls_4[0])}")
        vol_xml_trees = xmle.gen_xml_trees(xmls_2 + xmls_4)

        print("\nExtracting catalogue entries from xmls")
        lines, xml_track_df = xmle.extract_lines_for_vol(vol_xml_trees)
        title_shelfmarks, title_indices, ordered_lines = xmle.find_headings(lines)
        entry_df = xmle.extract_catalogue_entries(ordered_lines, title_indices, title_shelfmarks, xml_track_df)
        print(f"Extracted {len(entry_df)} entries")

        out_path = f"data\\processed\\BMC_{i}"
        print(f"Saving catalogue entries to {out_path}")
        if not os.path.exists(out_path):
            os.makedirs(out_path)

        entry_df.to_csv(os.path.join(out_path, "catalogue_entries_separate_sms.csv"), index=False)

        # xmle.save_poorly_scanned_pages(xmle.get_poorly_scanned_pages(current_volume, xmls), out_path)
        # print("Saving raw txt files")
        # # entry_df.groupby(by=["xml", "shelfmark"]).progress_apply(lambda x: xmle.groupby_save(x, outpath))
        # # print("Saving split txt files")
        # # xmle.saveSplitTxt(allTitleIndices, allLines, os.path.join(out_path, "splittextfiles"), titleRefs)
        # xmle.save_xml(lines, title_indices, title_shelfmarks, out_path)