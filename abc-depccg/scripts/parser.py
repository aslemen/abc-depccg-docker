#!/usr/bin/python3

import typing

from collections import namedtuple
import itertools
import argparse
import sys
import os
import json
import re
import parsy
import pathlib

# ======
# 1. Category Parser and Translators
# ======
"""
A tranalation table that translates atomic categories in the depccg format
    to those in the ABC Treebank format.
In fact, what this does is just get rid of brackets.

Examples
--------
"S[m]" -> "Sm"
"""
pCAT_BASE_trans_table: typing.Dict[int, str] = (
    str.maketrans(
        {
            "[": "",
            "]": ""    
        }
    )
)

@parsy.generate
def pCAT_BASE():
    """
    A parsy parser and translator of atomic depccg categories 
        into abstract representations of CG categories.

    Examples
    --------
    "S[m]" -> {"type": "BASE", "lit": "Sm"}
    """

    cat = yield parsy.regex(r"[^()\\/]+")

    return {
        "type": "BASE",
        "lit": cat.translate(pCAT_BASE_trans_table)
    }
# === END ===

@parsy.generate
def pCAT_COMP_LEFT():
    """
    A parsy parser and translator of left-functor depccg categories 
        into abstract representations of CG categories.

    Examples
    --------
    "S[m]\\PP[s]\\PP[o]" -> 
    {
        "type": "L", 
        "antecedent": {
                "type": "Base",
                "lit": "PPo",
            }, 
        "consequence": {
            "type": "L":
            "antecedent": {
                "type": "Base",
                "lit": "PPs",
            }, 
            "consequence": {
                "type": "Base",
                "lit": "Sm",
            }, 
        }
    """

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
    """
    A parsy parser and translator of right-functor depccg categories 
        into abstract representations of CG categories.

    Examples
    --------
    "S[m]/PP[s]/PP[o]" -> 
    {
        "type": "R", 
        "antecedent": {
                "type": "Base",
                "lit": "PPo",
            }, 
        "consequence": {
            "type": "R":
            "antecedent": {
                "type": "Base",
                "lit": "PPs",
            }, 
            "consequence": {
                "type": "Base",
                "lit": "Sm",
            }, 
        }
    """

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
    """
    A parsy parser and translator of parenthesized depccg categories 
        into abstract representations of CG categories.
    """

    yield parsy.match_item("(")
    cat = yield pCAT
    yield parsy.match_item(")")

    return cat
# === END ===

"""
The root paraser and translator of any depccg categories 
    into abstract representations of CG categories.
"""
pCAT = pCAT_COMP_LEFT

def parse_cat(text: str) -> dict:
    """
    Parse powered by parsy an depccg category and translate it into an abstract representation for CG categories.

    Parameters
    ----------
    text : str
        A string representation of an depccg category.
    
    Returns
    -------
    res : dict
        An abstract representation of the given input.

    Examples
    --------
    >>> parse_cat("(S[m]/S[m])/(S[p]\\PP[s]\\PP[o])")
    {'type': 'R',
        'antecedent': {'type': 'L',
            'antecedent': {'type': 'BASE', 'lit': 'PPo'},
            'consequence': {'type': 'L',
                'antecedent': {'type': 'BASE', 'lit': 'PPs'},
                'consequence': {'type': 'BASE', 'lit': 'Sp'}}},
        'consequence': {'type': 'R',
            'antecedent': {'type': 'BASE', 'lit': 'Sm'},
            'consequence': {'type': 'BASE', 'lit': 'Sm'}}}
    """

    return pCAT.parse(text)
# === END ===

def translate_cat_TLG(cat: dict) -> str:
    """
    Print an abstract representation of a CG category in the ABC Treebank format.

    Parameters
    ----------
    cat : dict
        An abstract representation of a CG category.
    
    Returns
    -------
    res : str
        A string representation in the ABC Treebank format.


    Examples
    --------
    >>> translate_cat_TLG(parse_cat("(S[m]/S[m])/(S[p]\\PP[s]\\PP[o])"))
    '<<Sm/Sm>/<PPo\\<PPs\\Sp>>>'
    """

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
    """
    Print an abstract representation of a CG category in the ABC Treebank format.

    Parameters
    ----------
    text : str
        A string representation of an depccg category.
    
    Returns
    -------
    res : str
        A string representation in the ABC Treebank format.

    Examples
    --------
    >>> parse_cat_translate_TLG("(S[m]/S[m])/(S[p]\\PP[s]\\PP[o])"))
    '<<Sm/Sm>/<PPo\\<PPs\\Sp>>>'

    Notes
    --------
    parse_cat_translate_TLG(str) == translate_cat_TLG(parse_cat(str))

    """
    return translate_cat_TLG(parse_cat(text))
# === END ===

# ======
# 2. Tree formatters
# ======
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

# =======
# 3. Janome Tokenizers
# ======
JanomeLexEntry = namedtuple(
    "JanomeLexEntry",
    (
        "surface", "left_id", "right_id", "cost",
        "part_of_speech",
        "infl_type", "infl_form", "base_form", "reading", "phonetic"
    )
)

def generate_janome_userdic(
    dic: typing.List[typing.Tuple[typing.Any]]
) -> typing.Set[JanomeLexEntry]:
    # ------
    # collecting heads
    # ------
    # -- はず（名詞，非自立）
    entries_hazu = [
        JanomeLexEntry(*e)
        for e in dic
        if re.match(r"^(はず|ハズ|筈)$", e[7]) and re.match(r"名詞,非自立", e[4])
    ]

    # -- か（終助詞）
    entries_ka = [
        JanomeLexEntry(*e)
        for e in dic
        if re.match(r"^か$", e[7])
    ]

    # -- ない（形容詞）
    entries_nai_adj = [
        JanomeLexEntry(*e) 
        for e in dic
        if re.match(r"^(ない|無い)$", e[7]) and re.match(r"形容詞", e[4])
    ]

    # -- ない（助動詞）
    # -- ん（助動詞）
    entries_nai_aux = [
        JanomeLexEntry(*e)
        for e in dic
        if (
            re.match(r"ん", e[7]) 
            or (re.match(r"^ない$", e[7]) and re.match(r"助動詞", e[4]))
        )
    ]

    # -- ある（自立動詞）
    entries_aru = [
        JanomeLexEntry(*e)
        for e in dic
        if re.match(r"^(ある|有る)$", e[7]) and re.match(r"動詞,自立", e[4])
    ]

    # ------
    # generating entries
    # ------
    res: typing.Set[JanomeLexEntry] = set()

    # -- はずがない・ある
    res.update(
        head._replace(
            surface = (
                hazu.surface 
                + case["surface"] 
                + head.surface
            ),
            left_id = hazu.left_id,
            # right_id = ,
            cost = head.cost - 10000,
            #pos_major = ,
            #pos_minor1 = ,
            #pos_minor2 = ,
            #pos_minor3 = ,
            #infl_type = ,
            #infl_form =, 
            base_form = (
                hazu.base_form 
                + case["base_form"] 
                + head.base_form
            ), 
            reading = (
                hazu.reading 
                + case["reading"] 
                + head.reading
            ), 
            phonetic = (
                hazu.phonetic 
                + case["phonetic"] 
                + head.phonetic
            )
        )
        for hazu in entries_hazu
        for case in [
            {
                "surface": s,
                "base_form": s,
                "reading": r,
                "phonetic": p
            } for s, r, p in (
                ("が", "ガ", "ガ"), ("ガ", "ガ", "ガ"),
                ("は", "ハ", "ワ"), ("ハ", "ハ", "ワ"),
                ("も", "モ", "モ"), ("モ", "モ", "モ"),
                ("の", "ノ", "ノ"), ("ノ", "ノ", "ノ"),
            )
        ]
        for head in itertools.chain(entries_nai_adj, entries_aru)
    )

    # -- かもしれない
    res.update(
        head._replace(
            surface = (
                ka.surface 
                + case["surface"] 
                + head.surface
            ),
            left_id = ka.left_id,
            # right_id = ,
            cost = head.cost - 10000,
            #pos_major = ,
            #pos_minor1 = ,
            #pos_minor2 = ,
            #pos_minor3 = ,
            #infl_type = ,
            #infl_form =, 
            base_form = (
                ka.base_form 
                + case["base_form"] 
                + head.base_form
            ), 
            reading = (
                ka.reading 
                + case["reading"] 
                + head.reading
            ), 
            phonetic = (
                ka.phonetic 
                + case["phonetic"] 
                + head.phonetic
            )
        )
        for ka in entries_ka
        for case in [
            {
                "surface": s,
                "base_form": s,
                "reading": "モシレ",
                "phonetic": "モシレ"
            } for s in (
                "もしれ",
                "モシレ",
                "も知れ",
                "モ知レ"
            )
        ]
        for head in entries_nai_aux
    )

    def _iter_nakya(nai_entry: JanomeLexEntry) -> typing.Iterator[JanomeLexEntry]:
        if re.match(r"仮定", nai_entry.part_of_speech):
            if re.match(r"縮約", nai_entry.part_of_speech):
                return (
                    nai_entry._replace(
                        surface = (
                            nai_entry.surface 
                            + ba["surface"]
                        ),
                        base_form = (
                            nai_entry.base_form 
                            + ba["base_form"] 
                        ), 
                        reading = (
                            nai_entry.reading 
                            + "バ"
                        ), 
                        phonetic = (
                            nai_entry.phonetic 
                            + "バ"
                        )
                    ) for ba in ("ば", "バ")
                )
            else:
                yield nai_entry
            # === END IF ===
        elif re.match(r"基本", nai_entry.part_of_speech):
            if re.match(r"縮約", nai_entry.part_of_speech):
                return (
                    nai_entry._replace(
                        surface = (
                            nai_entry.surface 
                            + to["surface"]
                        ),
                        base_form = (
                            nai_entry.base_form 
                            + to["base_form"] 
                        ), 
                        reading = (
                            nai_entry.reading 
                            + "ト"
                        ), 
                        phonetic = (
                            nai_entry.phonetic 
                            + "ト"
                        )
                    ) for to in ("と", "ト")
                )
        else:
            pass
        # === END IF ===
    # === END ===

    # -- なければならない
    res.update(
        head._replace(
            surface = (
                nakere.surface 
                + case["surface"] 
                + head.surface
            ),
            left_id = ka.left_id,
            # right_id = ,
            cost = head.cost - 10000,
            #pos_major = ,
            #pos_minor1 = ,
            #pos_minor2 = ,
            #pos_minor3 = ,
            #infl_type = ,
            #infl_form =, 
            base_form = (
                nakere.base_form 
                + case["base_form"] 
                + head.base_form
            ), 
            reading = (
                nakere.reading 
                + case["reading"] 
                + head.reading
            ), 
            phonetic = (
                nakere.phonetic 
                + case["phonetic"] 
                + head.phonetic
            )
        )
        for nakere in itertools.chain.from_iterable(
            _iter_nakya(nai) for nai in entries_nai_aux
        )
        for case in [
            {
                "surface": s,
                "base_form": s,
                "reading": rp,
                "phonetic": rp 
            } for s, rp in (
                ("なら", "ナラ"),
                ("ナラ", "ナラ"),
                ("成ら", "ナラ"),
                ("成ラ", "ナラ"),
                ("行ケ", "イケ"),
                ("行け", "イケ"),
                ("いけ", "イケ"),
                ("イケ", "イケ"),
            )
        ]
        for head in entries_nai_aux
    )
    return res
# === END ===

__Janome_Tokenizer: "janome.tokenizer.Tokenizer" = None

def __init_janome_tokenizer():
    if __Janome_Tokenizer:
        pass
    else:
        __reset_janome_tokenizer()
    # === END IF ===
# === END ===

def __reset_janome_tokenizer():
    import janome.tokenizer
    import janome.dic
    from janome.sysdic import connections
    import tempfile
    global __Janome_Tokenizer
    
    __Janome_Tokenizer = janome.tokenizer.Tokenizer()
    user_entries = generate_janome_userdic(
        __Janome_Tokenizer.sys_dic.entries.values()
    )

    with tempfile.NamedTemporaryFile(mode = "w") as user_dict_tf:
        for entry in user_entries:
            user_dict_tf.write(",".join(map(str, entry)))
            user_dict_tf.write("\n")
        # === END FOR entry ===

        __Janome_Tokenizer.user_dic = janome.dic.UserDictionary(
            user_dict_tf.name, 
            "utf8", "ipadic",
            connections
        )
    # === END WITH user_dict ===
# === END ===

def annotate_using_janome(sentences, tokenize = False):
    import depccg.tokens
    
    __init_janome_tokenizer()

    res = []
    raw_sentences = []
    for sentence in sentences:
        sentence = ''.join(sentence)
        tokenized = __Janome_Tokenizer.tokenize(sentence)
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
            model_path_abbr_root: pathlib.Path = pathlib.Path("/root/results")

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

# ======
# 4. Commandline wrappers
# ======
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
