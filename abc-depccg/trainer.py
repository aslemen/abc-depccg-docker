#!/usr/bin/python3
import typing
import io
import random

import os
import shutil
import pathlib
import datetime
import json

import depccg.tools.ja.keyaki_reader as kr
import allennlp.common.params as allp
import allennlp.common.util as allu
import allennlp.commands.train as allct
allu.import_submodules("depccg.models.my_allennlp")

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
            A pair of categories which represents a permiited unary branching.
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

def mod_treebank(
    p_treebank: pathlib.Path,
    dir_output: pathlib.Path,
    mode: str
) -> ModderSettings:
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
    kr.TrainingDataCreator.create_traindata(
        modder_settings,
        mode = mode
    )

    # Add the list of categories to the modder settings
    with open(dir_output / "target.txt") as h_target:
        parser_settings["targets"] = list(
            filter(
                None,
                map(parse_mod_target_line, h_target)
            )
        )
    # === END WITH h_target ===            

    # Add the list of unary rules to the modder settings
    with open(dir_output / "unary_rules.txt") as h_unary:
        parser_settings["unary_rules"] = list(
            filter(
                None,
                map(parse_mod_unary_line, h_unary)
            )
        )
    # === END WITH h_unary ===       

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
    DIR_OUTPUT_WVECT.mkdir()

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

    info_treebank_all: dict = mod_treebank(
        DIR_OUTPUT_SOURCE / "all.psd",
        DIR_OUTPUT_MODTREEBANK_ALL,
        mode = "train"
    )

    DIR_OUTPUT_MODTREEBANK_TRAIN = DIR_OUTPUT_MODTREEBANK / "train"
    DIR_OUTPUT_MODTREEBANK_TRAIN.mkdir()

    info_treebank_train: dict = mod_treebank(
        DIR_OUTPUT_SOURCE / "training.psd",
        DIR_OUTPUT_MODTREEBANK_TRAIN,
        mode = "train"
    )

    DIR_OUTPUT_MODTREEBANK_TEST = DIR_OUTPUT_MODTREEBANK / "test"
    DIR_OUTPUT_MODTREEBANK_TEST.mkdir()

    info_treebank_test: dict = mod_treebank(
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
        for entry in info_treebank_all["parser_settings"]["targets"]:
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
    # 5. Execute the trainer
    # ------
    allct.train_model(
        params = trainer_settings,
        serialization_dir = DIR_OUTPUT_MODEL
    )

    # ------
    # 6. Dump parser settings
    # ------
    with open(
        DIR_OUTPUT / "config_parser_abc.json",
        "w+"
    ) as h_parserconf:
        json.dump(
            info_treebank_train["parser_settings"],
            h_parserconf
        )
    # === END WITH ===
# === END IF ===