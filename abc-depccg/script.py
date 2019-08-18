#!/usr/bin/python3
import typing
import io
import random

import os
import shutil
import tempfile
import pathlib
import datetime
import json

import depccg.tools.ja.keyaki_reader as kr
import allennlp.common.params as allp
import allennlp.common.util as allu
import allennlp.commands.train as allct
allu.import_submodules("depccg.models.my_allennlp")

class ModderSettings: pass

def parse_mod_target_line(line: str) -> typing.Union[str]:
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
    entry_tokens = line.split()

    if len(entry_tokens) < 2:
        return []
    else:
        return entry_tokens[0:2]
    # === END IF ===
# === END ===

def mod_treebank(
    p_treebank: pathlib.Path
) -> dict:
    dir_treebank_mod = tempfile.TemporaryDirectory()
    p_DIR_TREEBANK_MOD: pathlib.Path = pathlib.Path(dir_treebank_mod.name)

    modder_settings = ModderSettings()
    modder_settings.PATH = p_treebank
    modder_settings.OUT = p_DIR_TREEBANK_MOD
    modder_settings.word_freq_cut = 5
    modder_settings.afix_freq_cut = 5
    modder_settings.char_freq_cut = 5
    modder_settings.cat_freq_cut = 5

    kr.TrainingDataCreator.create_traindata(modder_settings)

    parser_settings = dict()

    with open(p_DIR_TREEBANK_MOD / "target.txt") as h_target:
        parser_settings["targets"] = list(
            filter(
                None,
                map(parse_mod_target_line, h_target)
            )
        )
    # === END WITH h_target ===            

    with open(p_DIR_TREEBANK_MOD / "unary_rules.txt") as h_unary:
        parser_settings["unary_rules"] = list(
            filter(
                None,
                map(parse_mod_unary_line, h_unary)
            )
        )
    # === END WITH h_unary ===       

    return {
        "dir_modded": dir_treebank_mod,
        "path_dir_modded": p_DIR_TREEBANK_MOD,
        "parser_settings": parser_settings
    }     
# === END ===

def get_rand():
    return random.uniform(0, 100)
# === END ===

# ======
# Main Procedure
# ======
if __name__ == "__main__":
    # ------
    # Constants
    # ------
    DIR_TREEBANK: pathlib.Path = pathlib.Path("/root/treebank")

    FILE_TRAINER_SETTINGS: pathlib.Path = pathlib.Path(
        "/root/supertagger.jsonnet"
    )

    FILE_TREEBANK_ALL: str
    FILE_TREEBANK_TRAIN: str
    FILE_TREEBANK_TEST: str
    FILE_VOCAB_LIST: str
    DIR_VOCAB: str

    INT_TRAINTEST_RATIO: int = 80

    # ------
    # Divide trees to the training / test sets
    # ------
    with tempfile.NamedTemporaryFile(
        mode = "w",
        delete = False
    ) as h_treebank_all, tempfile.NamedTemporaryFile(
        mode = "w",
        delete = False
    ) as h_treebank_train, tempfile.NamedTemporaryFile(
        mode = "w",
        delete = False
    ) as h_treebank_test:
        FILE_TREEBANK_ALL = pathlib.Path(h_treebank_all.name)
        FILE_TREEBANK_TRAIN = pathlib.Path(h_treebank_train.name)
        FILE_TREEBANK_TEST = pathlib.Path(h_treebank_test.name)

        for treefile in DIR_TREEBANK.glob("**/*.psd"):
            with open(treefile, "r") as h_treefile:
                for line in h_treefile:
                    if get_rand() < INT_TRAINTEST_RATIO:
                        h_treebank_train.write(line)
                    else:
                        h_treebank_test.write(line)
                    # === END IF ===

                    h_treebank_all.write(line)                
                # === END FOR line ===
            # === END WITH h_treefile ===
        # === END FOR treefile ===
    # === END WITH h_(temporary files) ===

    # ------
    # Modify trees and collect info
    # ------
    info_treebank_all: dict = mod_treebank(FILE_TREEBANK_ALL)
    info_treebank_train: dict = mod_treebank(FILE_TREEBANK_TRAIN)
    info_treebank_test: dict = mod_treebank(FILE_TREEBANK_TEST)

    # ------
    # Configure the vocabulary directory
    # ------
    DIR_VOCAB = tempfile.TemporaryDirectory()
    p_DIR_VOCAB = pathlib.Path(DIR_VOCAB.name)

    shutil.copytree(
        "/root/lex-model-depccg-ja/vocabulary",
        p_DIR_VOCAB / "vocab"
    )

    # Overwrite the vocabulary list
    with open(p_DIR_VOCAB / "vocab" / "head_tags.txt", "w") as h_headtags:
        h_headtags.write("@@UNKNOWN@@\n")
        for entry in info_treebank_all["parser_settings"]["targets"]:
            h_headtags.write(entry)
            h_headtags.write("\n")
        # === END FOR entry ===
    # === END with h_headtags ===

    # ------
    # Configure the trainer
    # ------
    trainer_settings: allp.Params = (
        allp.Params.from_file(
            FILE_TRAINER_SETTINGS,
            ext_vars = {
                "vocab": str(
                    p_DIR_VOCAB / "vocab"
                ), # 違う．フォルダごとでなければならない
                "train_data": str(
                    info_treebank_train["path_dir_modded"] 
                    / "traindata.json"
                ),
                "test_data": str(
                    info_treebank_test["path_dir_modded"] 
                    / "traindata.json"
                ),
                "gpu": "0"
            }
        )
    )

    p_DIR_OUTPUT: pathlib.Path = pathlib.Path(
        "/root/res/" 
    ) / datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    # ------
    # Execute the trainer
    # ------
    allct.train_model(
        params = trainer_settings,
        serialization_dir = (
            p_DIR_OUTPUT
        )
    )


    # ------
    # Copy parser settings
    # ------
    with open(
        p_DIR_OUTPUT / "config_parser_abc.json",
        "w+"
    ) as h_parserconf:
        json.dump(
            info_treebank_train["parser_settings"],
            h_parserconf
        )
    # === END WITH ===

    # ------
    # Close temporary files
    # ------
    try:
        os.remove(FILE_TREEBANK_ALL)
        os.remove(FILE_TREEBANK_TRAIN)
        os.remove(FILE_TREEBANK_TEST)
        os.remove(FILE_VOCAB_LIST)

        for info in (
            info_treebank_all, 
            info_treebank_train, 
            info_treebank_test,
            DIR_VOCAB
        ):
            if info["dir_modded"]:
                info["dir_modded"].cleanup()
            # === END IF ===
        # === END FOR info ===
    except OSError:
        pass
    # === END TRY ===
# === END IF ===