import os
import shutil
import re
import xml
from xml.dom import minidom
import numpy as np
import pandas as pd
from langdetect import detect
from tqdm import tqdm


# Extracts all lines for given xmltree
def extractLines(root: xml.etree.ElementTree.Element):
    lines = []

    textRegions = [x for x in root[1] if len(x) > 2]  # Empty Text Regions Removed

    if len(textRegions) % 2 == 0:
        half = int(len(textRegions) / 2)
        newTextRegions = []
        for x in range(half):
            newTextRegions.append(textRegions[x])
            newTextRegions.append(textRegions[x + half])
        textRegions = newTextRegions

    for textRegion in textRegions:
        textLines = textRegion[1:-1]  # Skip coordinate data in first child
        for textLine in textLines:
            lines.append(textLine[-1][0].text)  # Text equivalent for line
    return lines


# Extracts lines for a collection of xmltrees
def extractLinesForVol(vol: dict[str: xml.etree.ElementTree.Element]):
    allLines = []
    xml_idx = []
    for xml, root in tqdm(vol.items()):
        rootLines = extractLines(root)
        allLines += rootLines
        xml_idx += [xml] * len(rootLines)
    xml_track_df = pd.DataFrame(
        data={
            "xml": xml_idx,
            "line": allLines
        }
    )
    return allLines, xml_track_df


# Regular expressions used in the detection og headings
caps_regex = re.compile("[A-Z][A-Z][A-Z]+")
c_num_regex = re.compile("C\.[0-9]")  # C number title references
i_num_regex = re.compile("I[ABC]\.\s[0-9]")  # I number title references
date_regex = re.compile("1[45][0-9][0-9]")  # Date format regexes (specific to this volume)


# Looks for identifying marks of a catalogue heading beginning
def checkLine(line: str):
    if line is not None:
        return i_num_regex.search(line) or c_num_regex.search(line)
    else:
        return False


# Looks for identifying marks of a catalogue heading ending
def dateCheck(titlePart: str):
    return date_regex.search(titlePart) or "Undated" in titlePart


# NOT USED RIGHT NOW
def getInitTitle(lines: list[str]):
    output = ""
    title = False
    for line in lines[:5]:
        output += line
        if dateCheck(line):
            title = True
            break
    if title and len(caps_regex.findall(output)) > 0:
        return output
    else:
        return " ".join(caps_regex.findall("".join(lines[:5])))


# Finds all headings from a list of lines
def findHeadings(allLines: list[str]):
    titles = []  # The names of the titles
    index = -1
    allTitleIndices = []
    for x in range(len(allLines)):
        index += 1
        line = allLines[x]
        if line is not None:
            if checkLine(line):  # If start of chapter found
                output = line
                endFound = False
                titleIndices = [index]
                for y in range(1, 7):
                    try:
                        titlePart = allLines[x + y]
                    except:
                        pass
                    if checkLine(titlePart):  # If a new chapter begins during the current title
                        break
                    output += titlePart
                    titleIndices.append(index + y)
                    if dateCheck(titlePart):  # If end of a chapter found
                        endFound = True
                        break

                if endFound and len(caps_regex.findall(output)) > 0:  # Title has to contain all uppercase words
                    titles.append(output)
                    allTitleIndices.append(titleIndices)

    #  if (len(getInitTitle(allLines)) > 0):
    #    titles = [getInitTitle(allLines)] + titles
    return titles, allTitleIndices


# Extracts the title reference number from a line for I numbers (e.g. IB929)
def getINumTitle(fullTitle: str):
    if fullTitle[:14].count(".") >= 2:
        return ".".join(fullTitle.split(".")[:2])
    else:
        return fullTitle[:9]


# Extracts the title reference number from a line for C numbers (only found in 1 volume)
def getCNumTitle(fullTitle: str):
    if fullTitle[:14].count(".") >= 4:
        return ".".join(fullTitle.split(".")[:4])
    else:
        return fullTitle[:10]


# Finds the associated title reference from a given line
def findTitleRef(fullTitle: str):
    if i_num_regex.search(fullTitle) is not None:
        ref = getINumTitle(fullTitle[i_num_regex.search(fullTitle).start():])
        return ref.replace("/", ".")
    elif c_num_regex.search(fullTitle) is not None:
        ref = getCNumTitle(fullTitle[c_num_regex.search(fullTitle).start():])
        return ref.replace("/", ".")
    else:
        print("Unrecognized title format")


def genTitleRefs(allTitleIndices: list[list[int]], allLines: list[str]):

    titleRefs = []

    for itr in range(len(allTitleIndices[:-1])):
        titleIndices = allTitleIndices[itr]
        fullTitle = "".join([allLines[x] for x in titleIndices])
        titleRef = findTitleRef(fullTitle)
        titleRefs.append(titleRef)

    return titleRefs


# Generates an XML document based on the found catalogue headings in the document
def generateXML(allTitleIndices: list[list[int]], allLines: list[str], titleRefs):
    xml = minidom.Document()
    text = xml.createElement('text')

    for itr in range(len(allTitleIndices[:-2])):
        titleIndices = allTitleIndices[itr]
        catalogueIndices = [x for x in range(titleIndices[-1], allTitleIndices[itr + 1][0])]
        fullTitle = "".join([allLines[x] for x in titleIndices])
        titleRef = findTitleRef(fullTitle)

        chapter = xml.createElement('chapter')
        chapter.setAttribute("REFERENCE", titleRefs[itr + 1])
        chapter.setAttribute("HEADING", fullTitle)

        for catalogueIndex in catalogueIndices:
            line = xml.createElement('line')
            line.setAttribute("CONTENT", allLines[catalogueIndex])
            chapter.appendChild(line)

        text.appendChild(chapter)

    xml.appendChild(text)
    return xml


# Saves the generated XML for the headings into a chosen location
def saveXML(allTitleIndices, allLines, out_path, titleRefs):
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    xml = generateXML(allTitleIndices, allLines, titleRefs)
    xml_str = xml.toprettyxml(indent="\t")
    save_path_file = out_path + "/headings.xml"
    with open(save_path_file, "w", encoding="utf-8") as f:
        f.write(xml_str)
        f.close()
    # shutil.make_archive(path, 'zip', path)


# Saves all of the text, split by chapters, into text files
def saveRawTxt(allTitleIndices, allLines, xml_track_df, out_path, titleRefs):
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    for itr in tqdm(range(len(allTitleIndices[:-2]))):
        titleIndices = allTitleIndices[itr]
        catalogueIndices = [x for x in range(titleIndices[1], allTitleIndices[itr + 1][0])]
        fullTitle = "".join([allLines[x] for x in titleIndices])
        titleRef = findTitleRef(fullTitle)

        xml = xml_track_df.loc[titleIndices[1], "xml"]
        clean_shelfmark = titleRefs[itr + 1].replace(".", "_").replace(" ", "")
        save_path_file = os.path.join(out_path, f"{xml[:-4]}_{clean_shelfmark}.txt")
        with open(save_path_file, "w", encoding="utf-8") as f:
            # f.write(fullTitle + "\n")
            for lineIndex in catalogueIndices:
                f.write(allLines[lineIndex] + "\n")
        # shutil.make_archive(path, 'zip', path)


# Splits up a document by the detected language
def splitByLanguage(lines):
    splitLines = []
    firstLineLan = ""
    secondLineLan = ""
    try:
        firstLineLanLan = detect(lines[0])
    except:
        firstLineLan = "can't find language"
    try:
        secondLineLan = detect(lines[1])
    except:
        secondLineLan = "can't find language"
    first2Lines = [firstLineLan, secondLineLan]
    languageEn = first2Lines.count("en") == 2
    firstLanguage = languageEn
    currentBlock = [lines[0], lines[1]]
    for ind in range(2, len(lines[:-1])):
        cLineLan = ""
        nLineLan = ""
        try:
            cLineLan = detect(lines[ind])
        except:
            cLineLan = "can't find language"
        try:
            nLineLan = detect(lines[ind + 1])
        except:
            nLineLan = "can't find language"
        next2Lines = [cLineLan, nLineLan]
        if (next2Lines.count("en") == 0) and languageEn:
            languageEn = False
            splitLines.append(currentBlock)
            currentBlock = [lines[ind]]
        elif (next2Lines.count("en") == 2) and (not languageEn):
            languageEn = True
            splitLines.append(currentBlock)
            currentBlock = [lines[ind]]
        else:
            currentBlock.append(lines[ind])
    currentBlock.append(lines[-1])
    splitLines.append(currentBlock)
    return firstLanguage, splitLines


# Saves all of the text, split by chapters into text files where non-english sections of text are removed
def saveSplitTxt(allTitleIndices, allLines, out_path, titleRefs):
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    for itr in tqdm(range(len(allTitleIndices[:-2]))):
        titleIndices = allTitleIndices[itr]
        catalogueIndices = [x for x in range(titleIndices[1], allTitleIndices[itr + 1][0])]
        fullTitle = "".join([allLines[x] for x in titleIndices])
        titleRef = findTitleRef(fullTitle)

        catalogueLines = [allLines[x] for x in catalogueIndices]
        firstLanguage, splitCatalogueLines = splitByLanguage(catalogueLines)

        save_path_file = os.path.join(out_path, titleRefs[itr + 1].replace(".", "-") + ".txt")
        with open(save_path_file, "w", encoding="utf-8") as f:
            f.write(fullTitle + "\n")
            languageEn = firstLanguage
            for blockLines in splitCatalogueLines:
                if languageEn:
                    # f.write("##########ENGLISH SECTION##########\n")
                    for line in blockLines:
                        f.write(line + "\n")
                else:
                    f.write("-----------------------------------\n")
                    f.write("NON-ENGLISH SECTION LASTING {} LINES\n".format(len(blockLines)))
                    f.write("-----------------------------------\n")
                languageEn = not languageEn
        # shutil.make_archive(path, 'zip', path)


# Returns the number of lines in a page which are too long
def numOutliersForPage(lines, std, mean, threshold=2):
    lengths = [len(x.split()) for x in lines if x is not None]
    lengths = [(x - mean) for x in lengths]
    lengths = [(x / std) for x in lengths]
    numOutliers = len([x for x in lengths if x > threshold])
    return numOutliers


# Find all of the poorly scanned pages in the input
def getPoorlyScannedPages(volumeRoot, fileNames):
    poorlyScannedPageNums = []

    # Get all the lines for the volume and find the mean and std for the line lengths across all volumes
    volLines, xml_check_df = extractLinesForVol(volumeRoot)
    lengths = [len(x.split()) for x in volLines if x is not None]
    mean = np.mean(lengths)
    std = np.std(lengths)

    # For every page (xmlroot) in the volume
    for root, filename in zip(volumeRoot.values(), fileNames):
        page = root
        pageLines = extractLines(page)
        numOutliers = numOutliersForPage(pageLines, std, mean)
        if numOutliers > 5:
            poorlyScannedPageNums.append(filename.decode("utf-8"))
    return poorlyScannedPageNums


# Save poorly scanned page numbers to a text file
def savePoorlyScannedPages(poorlyScanned, out_path):
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    save_path_file = os.path.join(out_path, "poorlyscanned.txt")
    with open(save_path_file, "w", encoding="utf-8") as f:
        for scan in poorlyScanned:
            f.write(scan + "\n")
    # shutil.make_archive(path, 'zip', path)


# Saves the raw text files, the text files split by language and the XML files
def saveAll(currentVolume, xmls, xml_track_df, allTitleIndices, allLines, path, titleRefs):
    # out_path = os.path.join(path, "generated")  # if you do want them to go into a sub_folder of the output loc
    out_path = path
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    savePoorlyScannedPages(getPoorlyScannedPages(currentVolume, xmls), out_path)
    print("Saving raw txt files")
    saveRawTxt(allTitleIndices, allLines, xml_track_df, os.path.join(out_path, "rawtextfiles"), titleRefs)
    print("Saving split txt files")
    saveSplitTxt(allTitleIndices, allLines, os.path.join(out_path, "splittextfiles"), titleRefs)
    saveXML(allTitleIndices, allLines, out_path, titleRefs)
    # shutil.make_archive(out_path, 'zip', out_path)
