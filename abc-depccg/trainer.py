#!/usr/bin/python3
import typing
import io
import random
import itertools
import functools

import os
import shutil
import pathlib
import datetime
import json

# ======
# Data Types
# ======
class ModderSettings:
    """
        Settings for the `depccg.tools.ja.keyaki_reader` modifier.
        Attributes are added dynamically.
    """
# === END CLASS ===

# ======
# Parser
# ======
def parse_mod_target_line(line: str) -> typing.Union[str]:
    """
        Parse a line of `target.txt` 
        (the list of categories occurring in the treebank) 
        in the directory of a digested treebank.

        Parameters
        ----------
        line : str
            A line of `target.txt`.

        Returns
        -------
        category : str, optional
            The category found in the given line.
            None when nothing is found.
    """
    entry_tokens = line.split()

    if not entry_tokens:
        return None
    # === END IF ===

    entry = entry_tokens[0]

    if entry in ["*START*", "*END*"]:
        return None
    else:
        return entry
    # === END IF ===
# === END ===

def parse_mod_unary_line(line: str) -> typing.List[str]:
    """
        Parse a line of `unary_rules.txt`
        (the list of unary rules in the treebank)
        in the directory of a digested treebank.

        Parameters
        ----------
        line : str
            A line of `unary_rules.txt`.

        Returns
        -------
        unary_rule : typing.List[str]
            A pair of categories which represents a permitted unary branching.
            The upper node goes to the first element of the list
            and the lower node to the second one.
            A empty list is returned 
            if the given line fails to represent a unary rule.
    """
    entry_tokens = line.split()

    if len(entry_tokens) < 2:
        return []
    else:
        return entry_tokens[0:2]
    # === END IF ===
# === END ===

CAT_CLAUSES: typing.Set[str] = {
    "S", "S[m]", "S[a]", "S[e]", "S[sub]", 
    "S[imp]", "S[smc]", "S[nml]", "S[rel]",
    "CP[t]", "CP[q]", "CP[x]", "CP[f]", "multi-sentence"
}

CAT_PPS : typing.Set[str] = {
    "PP[s]", "PP[s2]", "PP[o1]", "PP[o2]"
}

CAT_NPS: typing.Set[str] = {
    "NP", "QP", "DP"
}

CAT_PP_LISTS_ORTHODOX_PL: typing.Set[typing.List[str]] = {
    ("PP[s2]", "PP[s]",) ,
    
    ("PP[o1]", "PP[s]"),
    ("PP[o1]", "PP[s2]", "PP[s]"),

    ("PP[o2]", "PP[o1]", "PP[s]"),
    ("PP[o2]", "PP[o1]", "PP[s2]", "PP[s]"),

    ("CP[t]", "PP[o1]", "PP[s]"),
    ("CP[t]", "PP[o1]", "PP[s2]", "PP[s]"),
}
    
CAT_PP_LISTS_ORTHODOX = CAT_PP_LISTS_ORTHODOX_PL | {("PP[s]", )}
CAT_PP_LISTS_ORTHODOX_WITHZERO = CAT_PP_LISTS_ORTHODOX | {tuple()}

CAT_PP_LISTS_SCRAMBLED: typing.Dict[tuple, typing.Set[tuple]] = {
    ortho:(
        set(
            itertools.permutations(ortho)
        ).difference(ortho)
    )
    for ortho in CAT_PP_LISTS_ORTHODOX_PL
}

    
def generate_category(head: str, args: typing.List[str], is_bracketed = False) -> str:
    if args:
        return "{br_open}{others}\\{arg}{br_close}".format(
            br_open = "(" if is_bracketed else "",
            br_close = ")" if is_bracketed else "",
            arg = args[0],
            others = generate_category(head, args[1:], True)
        )
    else:
        return head
    # === END IF ===
# === END ===

@functools.lru_cache()
def gen_unary_rules() -> typing.List[typing.Tuple[str, str]]:
    res = []

    # ======
    # Scramblings
    # ======

    for ortho, scrs in CAT_PP_LISTS_SCRAMBLED.items():
        res.extend(
            (
                generate_category(cl, ortho),
                generate_category(cl, scr)
            )
            for scr in scrs
            for cl in CAT_CLAUSES
        )

    # ======
    # Covert pronominals
    # ======

    res.extend(
        (
            generate_category(cl, args[1:]),
            generate_category(cl, args)
        )
        for args in CAT_PP_LISTS_ORTHODOX
        for cl in CAT_CLAUSES
    )

    # ======
    # Adnominal clauses
    # ======
    res.extend(
        (
            f"{np}/{np}",
            generate_category("S[rel]", (arg, ))
        )
        for arg in CAT_PPS
        for np in CAT_NPS
    )

    # =====
    # Adverbial clauses
    # ======
    for cl, args in itertools.product(
            CAT_CLAUSES, 
            CAT_PP_LISTS_ORTHODOX_WITHZERO
    ):
        pred: str = generate_category(cl, args, is_bracketed = True)

        # Full
        res.append(
            (
                f"{pred}/{pred}",
                "S[a]"
            )
        )

        # Controlled
        res.append(
            (
                f"{pred}/{pred}",
                "S[a]\\PP[s]"
            )
        )
    # === END FOR ===

    # =====
    # Nominal Predicates
    # ======
    res.extend(
        (
            f"{cl}\\PP[s]",
            np
        )
        for cl in CAT_CLAUSES
        for np in CAT_NPS
    )
    # == END FOR ===

    # =====
    # Caseless DPs
    # ======
    for pp in CAT_PPS:
        res.append(
            (pp, "DP")
        )
    # === END FOR ===


    # ======
    # Other rules
    # ======

    res.extend(
        (
            ("DP", "NP"), # Covert Determiner
            ("DP", "QP"), # Covert Determiner

            ("CP[q]", "S[sub]"), # Covert question marker

            # Admoninal NPs??
            # ("NP/NP", "NP"), 
            ("NP/NP", "DP"), 
            ("NP/NP", "QP"), 

            # Adverbial NPs  (frequent ones only)
            # e.g. きょう，昨日
            # ("(S[m]\\PP[s])/(S[m]\\PP[s])", "NP"),
            # ("(S[sub]\\PP[s])/(S[sub]\\PP[s])", "NP"),
            ("(S[m]\\PP[s])/(S[m]\\PP[s])", "DP"),
            ("(S[e]\\PP[s])/(S[e]\\PP[s])", "DP"),
            ("(S[a]\\PP[s])/(S[a]\\PP[s])", "DP"),
            ("(S[rel]\\PP[s])/(S[rel]\\PP[s])", "DP"),
            ("(CP[f]\\PP[s])/(CP[f]\\PP[s])", "DP"),
            ("S[sub]/S[sub]", "DP"),
            ("S[a]/S[a]", "DP"),

            # Adverbial QPs
            ("(S[m]\\PP[s])/(S[m]\\PP[s])", "QP"),
            ("(S[a]\\PP[s])/(S[a]\\PP[s])", "QP"),
            ("S[m]/S[m]", "QP"),

            # Peculiar Srel
            ("NP/NP", "S[rel]"),

            # single NUM
            ("QP", "NUM"), 
        )
    )

    return res
# === END ===

def mod_treebank(
    p_treebank: pathlib.Path,
    dir_output: pathlib.Path,
    mode: str
) -> ModderSettings:
    import depccg.tools.ja.keyaki_reader as kr

    """
        Digest a raw treebank file via `depccg.tools.ja.keyaki_reader` and 
        dump the results to the designated output folder.
        The used settings is what this function returns.

        Parameters
        ----------
        p_treebank : pathlib.Path
            The path to the treebank, which is a single file.

        Returns
        -------
        parser_settings : ModderSettings
            A default set of settings of the digester,
            which may be necessary later.
    """
    modder_settings = ModderSettings()
    modder_settings.PATH = p_treebank
    modder_settings.OUT = dir_output
    modder_settings.word_freq_cut = 5
    modder_settings.afix_freq_cut = 5
    modder_settings.char_freq_cut = 5
    modder_settings.cat_freq_cut = 5

    # Do the digest
    if mode == "train":
        kr.TrainingDataCreator.create_traindata(
            modder_settings,
        )
        # Add the list of categories to the modder settings
        with open(dir_output / "target.txt") as h_target:
            modder_settings.targets = list(
                filter(
                    None,
                    map(parse_mod_target_line, h_target)
                )
            )
        # === END WITH h_target ===            

        # Add the list of unary rules to the modder settings

        modder_settings.unary_rules = gen_unary_rules()
    elif mode == "test":
        kr.TrainingDataCreator.create_testdata(
            modder_settings,
        )
    else:
        raise ValueError
    # === END IF ===

    return modder_settings
# === END ===

def get_rand() -> float:
    """
        Generate a random float number ranging from 0 to 100.

        Returns
        -------
        num : float
            A random float number.
    """
    return random.uniform(0, 100)
# === END ===

# ======
# Main Procedure
# ======
if __name__ == "__main__":
    import allennlp.common.params as allp
    import allennlp.common.util as allu
    import allennlp.commands.train as allct
    allu.import_submodules("depccg.models.my_allennlp")
    # ------
    # Constants
    # ------
    DIR_TREEBANK: pathlib.Path = pathlib.Path("/root/source/")
    """ 
        The path to the original treebank directory 
        in which data are dispersed in multiple files.
    """

    FILE_TRAINER_SETTINGS: pathlib.Path = pathlib.Path(
        "/root/supertagger.jsonnet"
    )
    """
        The path to the trainer settings.
    """

    DIR_WVECT: pathlib.Path = pathlib.Path(
        "/root/lex-model-depccg-ja/vocabulary"
    )
    """
        The path to the directory of the word-vector database.
    """

    INT_TRAINTEST_RATIO: int = 80
    """ 
        The ratio of the traning part to the whold treebank sentences.
    """

    # ------
    # 0. Construct the output folder
    # ------
    DIR_RES: pathlib.Path = pathlib.Path("/root/result/")

    DIR_OUTPUT: pathlib.Path = DIR_RES / datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    while DIR_OUTPUT.exists():
        DIR_OUTPUT: pathlib.Path = DIR_RES / datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    # === END ===
    DIR_OUTPUT.mkdir()

    DIR_OUTPUT_SOURCE: pathlib.Path = DIR_OUTPUT / "source"
    DIR_OUTPUT_SOURCE.mkdir()

    DIR_OUTPUT_MODTREEBANK: pathlib.Path = DIR_OUTPUT / "treebank_mod"
    DIR_OUTPUT_MODTREEBANK.mkdir()

    DIR_OUTPUT_WVECT: pathlib.Path = DIR_OUTPUT / "wvect"
    # DIR_OUTPUT_WVECT.mkdir() # will be made later by shutil

    DIR_OUTPUT_MODEL: pathlib.Path = DIR_OUTPUT / "model"
    DIR_OUTPUT_MODEL.mkdir()

    # ------
    # 1. Divide trees to the training / test sets
    # ------

    # Create temporary files for the treebank
    with open(
        DIR_OUTPUT_SOURCE / "all.psd",
        mode = "w"
    ) as h_treebank_all, open(
        DIR_OUTPUT_SOURCE / "training.psd",
        mode = "w"
    ) as h_treebank_train, open(
        DIR_OUTPUT_SOURCE / "testing.psd",
        mode = "w"
    ) as h_treebank_test:
        # Open and scan each file in the treebank
        for treefile in DIR_TREEBANK.glob("**/*.psd"):
            with open(treefile, "r") as h_treefile:
                # For each line (i.e. sentence) in the file
                for line in h_treefile:
                    # Pick up a random number and decide whether the sentence goes to the traning or the test part
                    if get_rand() < INT_TRAINTEST_RATIO:
                        h_treebank_train.write(line)
                    else:
                        h_treebank_test.write(line)
                    # === END IF ===

                    # Dump the tree to h_treebank_all 
                    h_treebank_all.write(line)                
                # === END FOR line ===
            # === END WITH h_treefile ===
        # === END FOR treefile ===
    # === END WITH h_(temporary files) ===

    # ------
    # 2. Digest the separated treebanks and collect info
    # ------
    DIR_OUTPUT_MODTREEBANK_ALL = DIR_OUTPUT_MODTREEBANK / "all"
    DIR_OUTPUT_MODTREEBANK_ALL.mkdir()

    info_treebank_all: ModderSettings = mod_treebank(
        DIR_OUTPUT_SOURCE / "all.psd",
        DIR_OUTPUT_MODTREEBANK_ALL,
        mode = "train"
    )

    DIR_OUTPUT_MODTREEBANK_TRAIN = DIR_OUTPUT_MODTREEBANK / "train"
    DIR_OUTPUT_MODTREEBANK_TRAIN.mkdir()

    info_treebank_train: ModderSettings = mod_treebank(
        DIR_OUTPUT_SOURCE / "training.psd",
        DIR_OUTPUT_MODTREEBANK_TRAIN,
        mode = "train"
    )

    DIR_OUTPUT_MODTREEBANK_TEST = DIR_OUTPUT_MODTREEBANK / "test"
    DIR_OUTPUT_MODTREEBANK_TEST.mkdir()

    info_treebank_test: ModderSettings = mod_treebank(
        DIR_OUTPUT_SOURCE / "testing.psd",
        DIR_OUTPUT_MODTREEBANK_TEST,
        mode = "test"
    )

    # ------
    # 3. Configure the word-vector directory
    # ------
    # Copy the directory to the new folder 
    shutil.copytree(
        DIR_WVECT,
        DIR_OUTPUT_WVECT
    )

    # Overwrite the vocabulary list
    with open(
        DIR_OUTPUT_WVECT / "head_tags.txt", 
        mode = "w"
    ) as h_headtags:
        h_headtags.write("@@UNKNOWN@@\n")
        for entry in info_treebank_all.targets:
            h_headtags.write(entry)
            h_headtags.write("\n")
        # === END FOR entry ===
    # === END with h_headtags ===

    # ------
    # 4. Configure the trainer
    # ------
    trainer_settings: allp.Params = (
        allp.Params.from_file(
            FILE_TRAINER_SETTINGS,
            ext_vars = {
                "vocab": str(
                    DIR_OUTPUT_WVECT
                ),
                "train_data": str(
                    DIR_OUTPUT_MODTREEBANK_TRAIN
                    / "traindata.json"
                ),
                "test_data": str(
                    DIR_OUTPUT_MODTREEBANK_TEST
                    / "testdata.json"
                ),
                "gpu": "0"
            }
        )
    )

    # ------
    # 5. Dump parser settings
    # ------
    with open(
        DIR_OUTPUT / "config_parser_abc.json",
        "w+"
    ) as h_parserconf:
        json.dump(
            vars(info_treebank_train),
            h_parserconf,
            default = str
        )
    # === END WITH ===

    # ------
    # 6. Execute the trainer
    # ------
    allct.train_model(
        params = trainer_settings,
        serialization_dir = DIR_OUTPUT_MODEL
    )
# === END IF ===