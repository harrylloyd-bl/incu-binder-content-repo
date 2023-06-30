import os
from src.data import xml_extraction as xmle

if __name__ == '__main__':

    for i in range(1, 3):
        two_col_loc = f"data\\raw\\BMC_{i}\\BMC_{i}_2_column_model_output\\page"
        four_col_loc = f"data\\raw\\BMC_{i}\\BMC_{i}_4_column_model_output\\page"
        current_volume = xmle.gather_2_4_col_xmls(two_col_loc, four_col_loc)

        print("\nExtrating catalogue entries from xmls")
        lines, xml_track_df = xmle.extract_lines_for_vol(current_volume)
        title_shelfmarks, title_indices = xmle.find_headings(lines)
        entry_df = xmle.extract_catalogue_entries(lines, title_indices, title_shelfmarks, xml_track_df)
        print(f"Extracted {len(entry_df)} entries")

        out_path = "data\\processed\\BMC_{i}"
        if not os.path.exists(out_path):
            os.makedirs(out_path)

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