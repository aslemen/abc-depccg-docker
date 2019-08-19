#!/usr/bin/python3

import typing

import argparse
import sys
import json

from depccg.parser import JapaneseCCGParser
from depccg.printer import print_
from depccg.token import japanese_annotator, annotate_XX
from depccg.combinator import (headfinal_combinator,
                               ja_forward_application,
                               ja_backward_application,
                               ja_generalized_forward_composition0,
                               ja_generalized_backward_composition0,
                               ja_generalized_backward_composition1,
                               ja_generalized_backward_composition2,
                               ja_generalized_backward_composition3,
                               ja_generalized_forward_composition0,
                               ja_generalized_forward_composition1,
                               ja_generalized_forward_composition2)



def main(args):
    # 使う組み合わせ規則 headfinal_combinatorでくるんでください。
    binary_rules = [
        headfinal_combinator(ja_forward_application()),         # 順方向関数適用
        headfinal_combinator(ja_backward_application()),        # 逆方向関数適用
        headfinal_combinator(
            ja_generalized_forward_composition0(
                '/', '/', '/', '>B'
            )
        ),     # 順方向関数合成 X/Y Y/Z -> X/Z
        headfinal_combinator(
            ja_generalized_backward_composition0(
                '\\', '\\', '\\', '<B1'
            )
        ),  # Y\Z X\Y -> X\Z
        headfinal_combinator(
            ja_generalized_backward_composition1(
                '\\', '\\', '\\', '<B2'
            )
        ),  # (X\Y)|Z W\X --> (W\Y)|Z
        headfinal_combinator(
            ja_generalized_backward_composition2(
                '\\', '\\', '\\', '<B3'
            )
        ),  # ((X\Y)|Z)|W U\X --> ((U\Y)|Z)|W
        headfinal_combinator(
            ja_generalized_backward_composition3(
                '\\', '\\', '\\', '<B4'
            )
        ),  # (((X\Y)|Z)|W)|U S\X --> (((S\Y)|Z)|W)|U
    ]

    # 単語分割にjanome使います。pip install janomeしてください。
    annotate_fun = (
        japanese_annotator['janome'] 
        if args.tokenize 
        else annotate_XX
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

    # 設定ファイルとallennlpのモデルからパーザを初期化
    parser = JapaneseCCGParser.from_json(
        args.model + "/config_parser_abc.json", 
        args.model, 
        **kwargs
    )

    # 入力の文を読む
    doc: typing.List[typing.List[str]]
    if args.input is None:
        doc = list(
            filter(
                None,
                (l.strip() for l in sys.stdin)
            )
        )
    else:
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
    res = parser.parse_doc(doc, batchsize=args.batchsize)
    
    # 木を出力
    print_(res, tagged_doc, format=args.format, lang='ja')

if __name__ == '__main__':
    parser = argparse.ArgumentParser('A* CCG parser')
    parser.set_defaults(func=lambda _: parser.print_help())

    parser.add_argument('-m',
                        '--model',
                        help='path to model directory')
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
                        default='auto',
                        choices=['auto', 'deriv', 'xml', 'conll', 'html', 'prolog', 'jigg_xml', 'ptb', 'json'],
                        help='output format')
    parser.add_argument('--tokenize',
                        action='store_true',
                        help='tokenize input sentences')

    main(parser.parse_args())
# === END IF ===