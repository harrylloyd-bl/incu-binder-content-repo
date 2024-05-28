import glob
from IPython.display import display
import pandas as pd
from PIL import Image, ImageDraw
from matplotlib import colormaps
from cycler import cycler


def split_word_locs(row):
    if len(row["xml_start_line"]) == 1:
        return [row["word_locations"]]
    else:
        return [row["word_locations"][start:end] for start, end in zip([0] + row["xml_start_line"], row["xml_start_line"])]


def gen_page_entries_lookup(df):
    xml_list = df["xmls"].sum()
    word_locs_split = df.apply(split_word_locs, axis=1).sum()

    page_entries_df = pd.DataFrame(data={"xml": xml_list, "word_locs": word_locs_split})
    page_entries_df["word_locs"] = page_entries_df["word_locs"].apply(lambda x: [x])

    page_entries_lookup = page_entries_df.groupby(by="xml", as_index=False).sum()
    pages_non_zeroed = page_entries_lookup["xml"].apply(lambda x: int(x.split("_")[-2]))
    page_entries_lookup["page"] = (pages_non_zeroed - (pages_non_zeroed.min() - 1)).values
    page_entries_lookup["n_entries"] = page_entries_lookup["word_locs"].apply(len)
    return page_entries_lookup.set_index("page")


def get_concat_h(ims):
    # all ims are not exactly same size - differ by maybe 10%
    widths = [im.width for im in ims]
    cumsum_width = [0] + [sum(widths[:i+1]) for i in range(len(widths))]
    total_width = sum([im.width for im in ims])
    dst = Image.new('RGBA', (total_width, ims[0].height))
    [dst.paste(im, (x_start, 0)) for im, x_start in zip(ims, cumsum_width[:-1])]
    return dst


def display_entry(df_row):
    xmls = df_row["xmls"]
    start_lines = df_row["xml_start_line"]
    vols = [xml.split("_")[-3] for xml in xmls]
    cols = [xml[-1] for xml in xmls]
    jpgs = [xml[:-2] for xml in xmls]
    image_paths = [glob.glob(f"../data/raw/BMC_{vol}_{col}/*/{jpg}.jpg")[0] for vol, col, jpg in
                   zip(vols, cols, jpgs)]

    # get an image
    word_locs = df_row["word_locations"]
    out_images = []
    for path, start, cutoff in zip(image_paths, [0] + start_lines, start_lines):
        with Image.open(path).convert("RGBA") as base:

            # make a blank image for the colour patches, initialized to transparent
            patches = Image.new("RGBA", base.size, (255, 255, 255, 0))

            draw = ImageDraw.Draw(patches)
            for line in word_locs[start:cutoff]:
                [draw.rectangle(word, fill=(237, 232, 74, 65)) for word in line]

            out = Image.alpha_composite(base, patches)

            width, height = base.width // 6, base.height // 6
            out_images.append(out.resize((width, height)))

    concat_out = get_concat_h(out_images)
    display(concat_out)

    return concat_out


colours = colormaps["Accent"].colors[:4]
colours = [[int(255 * x) for x in list(c)] + [65] for c in colours]
pastel_cycler = cycler(color=colours)


def display_page(page, page_entry_lookup):
    xml = page_entry_lookup.loc[page, "xml"]
    entries = page_entry_lookup.loc[page, "word_locs"]
    cc = pastel_cycler()
    colours = [c['color'] for c, _ in zip(cc, entries)]
    vol = xml.split("_")[-3]
    col = xml[-1]
    jpg = xml[:-2]
    path = glob.glob(f"../data/raw/BMC_{vol}_{col}/*/{jpg}.jpg")[0]

    with Image.open(path).convert("RGBA") as base:

        # make a blank image for the colour patches, initialized to transparent
        patches = Image.new("RGBA", base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(patches)

        for word_locs, colour in zip(entries, colours):
            for line in word_locs:
                [draw.rectangle(word, fill=tuple(colour)) for word in line]

            out = Image.alpha_composite(base, patches)

        width, height = base.width // 6, base.height // 6
        resized = out.resize((width, height))
        display(resized)
        return resized
