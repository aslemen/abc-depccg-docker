#!/usr/bin/python3

import typing

import argparse
import sys
import os
import json
import parsy
import pathlib

# ======

pCAT_BASE_trans_table = (
    str.maketrans(
        {
            "[": "",
            "]": ""    
        }
    )
)

@parsy.generate
def pCAT_BASE():
    cat = yield parsy.regex(r"[^()\\/]+")

    return {
        "type": "BASE",
        "lit": cat.translate(pCAT_BASE_trans_table)
    }
# === END ===

@parsy.generate
def pCAT_COMP_LEFT():
    cat1 = yield pCAT_COMP_RIGHT 
    cat_others = yield (
        parsy.match_item("\\") 
        >> (
             pCAT_COMP_RIGHT
        )
    ).many()

    res = cat1
    for cat_next in cat_others:
        res = {
            "type": "L",
            "antecedent": cat_next,
            "consequence": res,
        }
    return res
# === END ===

@parsy.generate
def pCAT_COMP_RIGHT():
    cat1 = yield pCAT_BASE | pCAT_PAR
    cat_others = yield (
        parsy.match_item("/") 
        >> (pCAT_BASE | pCAT_PAR)
    ).many()

    res = cat1
    for cat_next in cat_others:
        res = {
            "type": "R",
            "antecedent": cat_next,
            "consequence": res,
        }
    return res
# === END ===

@parsy.generate
def pCAT_PAR():
    yield parsy.match_item("(")
    cat = yield pCAT
    yield parsy.match_item(")")

    return cat
# === END ===

pCAT = pCAT_COMP_LEFT

def parse_cat(text: str) -> dict:
    return pCAT.parse(text)
# === END ===

def translate_cat_TLG(cat: dict) -> str:
    input_type = cat["type"]
    if input_type == "L":
        return f"<{translate_cat_TLG(cat['antecedent'])}\{translate_cat_TLG(cat['consequence'])}>"
    elif input_type == "R":
        return f"<{translate_cat_TLG(cat['consequence'])}/{translate_cat_TLG(cat['antecedent'])}>"
    else:
        return cat["lit"]
    # === END IF ===
# === END ===

def parse_cat_translate_TLG(text: str):
    return translate_cat_TLG(parse_cat(text))
# === END ===

def dump_tree_ABCT(tree: dict, stream: typing.TextIO) -> typing.NoReturn:
    cat = parse_cat_translate_TLG(tree["cat"])

    if "children" in tree.keys():
        stream.write(f"({cat}")

        for child in tree["children"]:
            stream.write(" ")
            dump_tree_ABCT(child, stream)
        # === END FOR child ===

        stream.write(")")
    else:
        if "surf" in tree:
            stream.write(
                f"({cat} {tree['surf']})"
            )
        elif "word" in tree:
            stream.write(
                f"({cat} {tree['word']})"
            )
        else:
            stream.write(
                f"({cat} ERROR)"
            )
    # === END IF ===
# === END ===

def annotate_using_janome(sentences, tokenize = False):
    import janome.tokenizer as janome_token
    
    user_dict_path: str = os.path.dirname(__file__) + "/abc-dict.csv"
    tokenizer = janome_token.Tokenizer(
        udic = (
            user_dict_path
                if pathlib.Path(user_dict_path).is_file()
                else ""
        )
    )
    import depccg.tokens

    res = []
    raw_sentences = []
    for sentence in sentences:
        sentence = ''.join(sentence)
        tokenized = tokenizer.tokenize(sentence)
        tokens = []

        for token in tokenized:
            pos, pos1, pos2, pos3 = token.part_of_speech.split(',')
            token = depccg.tokens.Token(
                word=token.surface,
                surf=token.surface,
                pos=pos,
                pos1=pos1,
                pos2=pos2,
                pos3=pos3,
                inflectionForm=token.infl_form,
                inflectionType=token.infl_type,
                reading=token.reading,
                base=token.base_form
            )
            tokens.append(token)
        raw_sentence = [token.surface for token in tokenized]
        res.append(tokens)
        raw_sentences.append(raw_sentence)

    return res, raw_sentences
# === END ===

def main(args):
    from depccg.parser import JapaneseCCGParser
    from depccg.printer import print_
    import depccg.tokens
    from depccg.combinator import (
        HeadfinalCombinator,
        JaForwardApplication,
        JaBackwardApplication,
        JaGeneralizedForwardComposition0,
        # JaGeneralizedForwardComposition1,
        # JaGeneralizedForwardComposition2,
        JaGeneralizedBackwardComposition0,
        JaGeneralizedBackwardComposition1,
        JaGeneralizedBackwardComposition2,
        JaGeneralizedBackwardComposition3,
    )

    # 使う組み合わせ規則 headfinal_combinatorでくるんでください。
    binary_rules = [
        HeadfinalCombinator(r) 
        for r in {
            JaForwardApplication(),             # 順方向関数適用
            JaBackwardApplication(),            # 逆方向関数適用
            JaGeneralizedForwardComposition0(   # 順方向関数合成 X/Y Y/Z -> X/Z
                '/', '/', '/', '>B'
            ),
            JaGeneralizedBackwardComposition0(  # Y\Z X\Y -> X\Z
                '\\', '\\', '\\', '<B1'
            ),
            JaGeneralizedBackwardComposition1(  # (X\Y)|Z W\X --> (W\Y)|Z
                '\\', '\\', '\\', '<B2'
            ),
            JaGeneralizedBackwardComposition2(  # ((X\Y)|Z)|W U\X --> ((U\Y)|Z)|W
                '\\', '\\', '\\', '<B3'
            ),
            JaGeneralizedBackwardComposition3(  # (((X\Y)|Z)|W)|U S\X --> (((S\Y)|Z)|W)|U
                '\\', '\\', '\\', '<B4'
            ),
        }
    ]

    # 単語分割にjanome使います。pip install janomeしてください。
    annotate_fun = (
        annotate_using_janome
            if args.tokenize 
            else depccg.tokens.annotate_XX
    )

    # パーザのオプション
    kwargs = dict(
        # unary ruleを使いすぎないようにペナルティを与えます。
        unary_penalty = 0.1,
        #nbest=,
        binary_rules = binary_rules,
        # ルートのカテゴリがこれらに含まれる木のみ解析結果として出力します
        possible_root_cats = [
            "S[m]", "FRAG", "INTJP", "CP[f]", "CP[q]", 
            "S[imp]", "CP[t]", "LST", "CP-EXL"
        ],
        use_seen_rules = False,
        use_category_dict = False,
        # 長い文は諦める
        max_length = 250,
        # 一定時間内に解析が終了しない場合解析を諦める
        max_steps = 10000000,
        # 構文解析にGPUをつかう
        gpu = -1
    )

    # ------
    # モデルへのパスの検索
    # ------
    
    def find_model_path(path_raw: typing.Union[str, pathlib.Path]) -> pathlib.Path:
        model_path_raw: pathlib.Path = pathlib.Path(path_raw)

        # 指定されたパスが相対パスであるのであれば，/root/resultsが省略されている可能性がある
        if (not model_path_raw.is_absolute()):
            model_path_abbr_root: pathlib.Path = pathlib.Path("/home/hayashi/results")

            # model_path_abbr_cand: /root/results/ が省略されていると見なした場合のパス
            model_path_abbr_cand: pathlib.Path = (
                model_path_abbr_root / model_path_raw
            )

            try:
                # そのパスが実在するのであれば
                if model_path_abbr_cand.is_dir():
                    sys.stderr.write(
                        f"[Parser] Model found in {model_path_abbr_cand}\n" 
                    )
                    return model_path_abbr_cand
                else:
                    pass
                # === END IF ===
            # 例外が生じた場合は，エラーメッセージを表示だけして，次の手順にうつる．
            except Exception as e:
                sys.stderr.write(e.args)
                sys.stderr.write(f"[Parser] Fail to find a model in '{model_path_abbr_cand}'. It will be treated as an non-abbreviated path.\n")
            finally:
                pass
            # === END TRY ===
        # === END IF ===

        # /root/results/... でモデルが見つからなければ，通常通りの検索をする．
        if model_path_raw.is_dir():
            return model_path_raw
        else:
            raise FileNotFoundError()
        # === END IF ===
    # === END ===

    # 設定ファイルとallennlpのモデルからパーザを初期化
    model_path_str: pathlib.Path = str(find_model_path(args.model))

    parser = JapaneseCCGParser.from_json(
        model_path_str + "/config_parser_abc.json", 
        model_path_str + "/model",
        **kwargs
    )

    # 入力の文を読む
    doc: typing.List[typing.List[str]]
    if args.input is None:
        # --input オプションが指定されていない場合，標準入力から文を読み込む
        doc = list(
            filter(
                None,
                (l.strip() for l in sys.stdin)
            )
        )
    else:
        # --input オプションが指定されている場合，それの引数である文字列を読み込む
        doc = list(
            filter(
                None,
                (l.strip() for l in args.input.splitlines())
            )
        )
    # === END IF ===

    tagged_doc = annotate_fun(
        [[word for word in sent.split(' ')] for sent in doc],
        tokenize = args.tokenize
    )

    if args.tokenize:
        tagged_doc, doc = tagged_doc
    # === END IF ===

    # 解析
    parsed_trees = parser.parse_doc(doc, batchsize=args.batchsize)
        
    # 木を出力
    if args.format == "abct":
        for i, (parsed, tokens) in enumerate(zip(parsed_trees, tagged_doc), 1):
            for tree, prob in parsed:
                tree_enh = {
                    "type": "ROOT",
                    "cat": "TOP",
                    "children": [
                        {
                            "cat": "COMMENT",
                            "surf": f"{{probability={prob}}}"
                        },
                        tree.json(tokens = tokens),
                        {
                            "cat": "ID",
                            "surf": str(i)
                        }
                    ]
                }
                dump_tree_ABCT(tree_enh, sys.stdout)
                sys.stdout.write("\n")
            # === END FOR ===
        # === END FOR ===
    else:
        print_(parsed_trees, tagged_doc, format=args.format, lang='ja')
    # === END IF ===
# === END ===

if __name__ == '__main__':
    parser = argparse.ArgumentParser('A* CCG parser')
    parser.set_defaults(func=lambda _: parser.print_help())

    parser.add_argument(
        '-m',
        '--model',
        help='path to a model directory'
    )

    parser.add_argument(
        '-i', '--input',
        type = typing.Union[str],
        default = None,
        help = "input to parse"
    )

    parser.add_argument('--batchsize',
                        type=int,
                        default=32,
                        help='batchsize in supertagger')
    parser.add_argument('-f',
                        '--format',
                        default='abct',
                        choices=["abct", 'auto', 'deriv', 'xml', 'conll', 'html', 'prolog', 'jigg_xml', 'ptb', 'json'],
                        help='output format')
    parser.add_argument('--tokenize',
                        action='store_true',
                        help='tokenize input sentences')

    main(parser.parse_args())
# === END IF ===