import pandas as pd
import src.data.xml_extraction as xmle

bll01_index_df = pd.read_csv(
    "data\\processed\\bll01_index.csv",
    encoding='latin-1',
    dtype={"c_sm": bool, "ig_sm": bool, "uncaptured_sm": bool}
)
bll01_index_df.rename(columns={'British Library shelfmark (852 $j)': "bll01_shelfmark", 'Record IDs (001)': "record_id"}, inplace=True)

# C re searches for preceeding `(`  and succeeding `)` so add these in manually during the apply
bll01_index_df["c_re"] = bll01_index_df["bll01_shelfmark"].apply(lambda x: xmle.c_re.search("(" + x))
bll01_index_df["ig_re"] = bll01_index_df["bll01_shelfmark"].apply(lambda x: xmle.ig_re.search(x))

true_c_sm = bll01_index_df["bll01_shelfmark"][bll01_index_df["c_sm"]]
true_ig_sm = bll01_index_df["bll01_shelfmark"][bll01_index_df["ig_sm"]]


def test_n_true_sms():
    assert len(true_c_sm) == 303
    assert len(true_ig_sm) == 10830


def test_re_performance():
    re_c_sm = bll01_index_df["c_re"].dropna().apply(lambda x: x.group())
    re_ig_sm = bll01_index_df["ig_re"].dropna().apply(lambda x: x.group())

    # Some shelfmarks aren't caught, or are caught in error
    # I've explained the logic for known errors for C and I/G shelfmarks
    # anything not in this list needs to be investigated

    c_sm_check = set(true_c_sm) ^ set(re_c_sm)
    known_c_sm_errors = {
        "C. 1. d. 2",  # part of `MAPS Maps C. 1. d. 2` - shouldn't be caught but overcomplicated to exclude
        "C. 1. d. 3",  # part of `MAPS Maps C. 1. d. 3` - shouldn't be caught but overcomplicated to exclude
        "C. 1. d. 6",  # the re caught part of below sm
        "C. 1. d. 6. ; C. 1. d. 7"  # the full sm, we won't catch the second part
    }

    assert c_sm_check == known_c_sm_errors

    ig_sm_check = set(true_ig_sm) ^ set(re_ig_sm)
    known_ig_sm_errors = {
        'G. 7726. (1',  # caught part of the next sm
        'G. 7726. (1. ); G. 7726. (2. )',  # won't catch full sm, or second part
        'G. 8284',  # caught part of the next sm
        'G. 8284. ; G. 8285',  # won't catch second part
        'IA. 18772',  # caught part of the next sm
        'IA. 18772. ,73',  # will be incomplete
        'IA. 22',  # caught part of the next sm
        'OC IA. 22',  # not sure what this sm actually is, but we won't catch
        'OC IA. 49865',  # same as prev line
        'IA. 2879. A',  # caught part of the next sm
        'IA. 2879. A. ; IA. 2880. A',  # won't catch second part
        'IA. 42066,42069',  # caught part of the next sm
        'IA. 42066,42069. &42070',  # won't catch second part
        'IA. 55330',  # caught part of the next sm
        'IA. 55330. Fragment: Sheet q2-q6, much mutilated',  # won't catch second part
        'IB. 20307',  # caught part of the next sm
        'IB. 20307. ; IB. 20297',  # won't catch second part
        'IB. 22635-7',  # caught part of the next sm
        'IB. 22635-7. ; IB. 22639',  # won't catch second part
        'IB. 355',  # part of `MAPS IB. 355` - shouldn't be caught but overcomplicated to exclude
        'IB. 55144a',  # caught part of the next sm
        "IB. 55144a. Fragment: 4 leaves of misimposed printer's waste",  # won't catch second part
        'IC. 17983',  # caught part of the next sm
        'IC. 17983. ; IC. 17950',  # won't catch second part
        'IC. 19562. &IC. 19543'  # won't catch second part
    }

    assert ig_sm_check == known_ig_sm_errors
