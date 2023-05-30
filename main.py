import os
import sys
import glob
from xml.etree import ElementTree as ET
from tqdm import tqdm
from src.data import xml_extraction as xmle

if __name__ == '__main__':
    page_xmls = []
    for i in range(8,9):
        network_loc = "\\\\ad\\collections\\TwoCenturies\\TwoCenturies IV\\Incunabula"
        suffix = "column pages Transkribus export"
        page_xmls.append(
            [
                os.path.join(network_loc, f"BMC_{i + 1} 2 {suffix}"),
                os.path.join(network_loc, f"BMC_{i + 1} 4 {suffix}")
            ]
        )

    # this one didn't work for some reason
    # 'BMC_5 2 column pages Transkribus export'

    for x in page_xmls:
        pageXMLLocation_2 = os.path.join(x[0], r"*\*\page\*.xml")
        pageXMLLocation_4 = os.path.join(x[1], r"*\*\page\*.xml")
        out_path = os.path.join(network_loc, "split_data\\test", os.path.basename(x[0]).split(" ")[0])
        attempts = 0
        while attempts < 3:
            xmls_2 = glob.glob(os.fsencode(pageXMLLocation_2))
            xmls_4 = glob.glob(os.fsencode(pageXMLLocation_4))

            if xmls_2 and xmls_4:
                xmls = xmls_2 + xmls_4
                break
            else:
                attempts += 1
                continue
        else:
            raise IOError(f"Failed to connect to {os.path.dirname(pageXMLLocation_2)}  {os.path.basename(pageXMLLocation_2)}/{os.path.basename(pageXMLLocation_4)}")

        xmlroots = {}

        print(f"\nGetting xml roots from {os.path.dirname(pageXMLLocation_2)}  {os.path.basename(pageXMLLocation_2)}/{os.path.basename(pageXMLLocation_4)}")
        for file in tqdm(xmls):
            fileName = os.fsdecode(file)
            attempts = 0
            while attempts < 3:
                try:
                    tree = ET.parse(fileName)
                    break
                except FileNotFoundError:
                    attempts += 1
                    continue
            else:
                raise FileNotFoundError(f"Failed to connect to: {fileName}")
            root = tree.getroot()
            xmlroots[os.path.basename(fileName)[5:]] = root  # take the label that spans different sections of a volume

        print("\nExtrating catalogue entries from xmls")
        currentVolume = {k: xmlroots[k] for k in sorted(xmlroots)}
        allLines, xml_track_df = xmle.extractLinesForVol(currentVolume)
        allLines = [line for line in allLines if line is not None]
        xml_track_df = xml_track_df.dropna(subset="line")
        titles, allTitleIndices = xmle.findHeadings(allLines)
        titleRefs = xmle.genTitleRefs(allTitleIndices, allLines)

        print(f"\nSaving catalogue entries to {out_path}\n")
        if not os.path.exists(out_path):
            os.makedirs(out_path)

        xmle.savePoorlyScannedPages(xmle.getPoorlyScannedPages(currentVolume, xmls), out_path)
        print("Saving raw txt files")
        xmle.saveRawTxt(allTitleIndices, allLines, xml_track_df, os.path.join(out_path, "rawtextfiles"), titleRefs)
        # print("Saving split txt files")
        # xmle.saveSplitTxt(allTitleIndices, allLines, os.path.join(out_path, "splittextfiles"), titleRefs)
        xmle.saveXML(allTitleIndices, allLines, out_path, titleRefs)

        # xmle.saveAll(
        #     currentVolume=currentVolume,
        #     xmls=xmls,
        #     xml_track_df=xml_track_df,
        #     allTitleIndices=allTitleIndices,
        #     allLines=allLines,
        #     path=out_path,
        #     titleRefs=titleRefs
        # )

    # savePoorlyScannedPages(getPoorlyScannedPages(currentVolume, os.listdir(directory)))
    # saveRawTxt(allTitleIndices, allLines)
    # saveSplitTxt(allTitleIndices, allLines)
    # saveXML(allTitleIndices, allLines)

    # discrepancy between number of titles and output files
