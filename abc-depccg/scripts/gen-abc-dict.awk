# requirement: lex.csv of 
BEGIN {
    FS = ",";
    OFS = ",";
}

function print_MeCab_entry(){
    for (i = 1; i <= 12; i++) {
        printf "%s" FS, $i;
    }

    print $13;
}

# ------------------------

function gen_hazu(form, kana, pron) {
    form_orig = $1;
    $1 = form $1; # 出現形

    #leftID_orig = $2;
    $2 = 15822; # 左文脈ID：「はず」に合わせる

    #ortho_orig = $15;
    $11 = "筈が"$15; # 書字形基本形

    #kana_orig = $25;
    $12 = kana $25; # 仮名形出現形

    #pron_orig = $14;
    $13 = pron $14; # 発音形

    print_MeCab_entry();

    $1 = form_orig;
    #$2 = leftID_orig;
    #$15 = ortho_orig;
    #$25 = kana_orig;
    #$14 = pron_orig;
}

# 「ない」（形容詞）
# 「亡い」を排除するために，「書字形出現形」（$13）にも制約をかけている
$12~/^無い$/ && $13~/無|な/ {
    # 「はずがない」系をつくる
    gen_hazu("はずが", "ハズガ", "ハズガ");
    gen_hazu("筈が", "ハズガ", "ハズガ");
    gen_hazu("ハズが", "ハズガ", "ハズガ");

    gen_hazu("はずも", "ハズモ", "ハズモ");
    gen_hazu("筈も", "ハズモ", "ハズモ");
    gen_hazu("ハズも", "ハズモ", "ハズモ");
    
    gen_hazu("はずは", "ハズハ", "ハズワ");
    gen_hazu("筈は", "ハズハ", "ハズワ");
    gen_hazu("ハズは", "ハズハ", "ハズワ");

    gen_hazu("はずの", "ハズノ", "ハズノ");
    gen_hazu("筈の", "ハズノ", "ハズノ");
    gen_hazu("ハズの", "ハズノ", "ハズノ");
}

# ------------------------

function gen_kamo(form) {
    form_orig = $1;
    $1 = form $1; # 出現形

    #leftID_orig = $2;
    $2 = 912; # 左文脈ID：「か」に合わせる

    #ortho_orig = $15;
    $11 = "かも知れ"$15; # 書字形基本形

    #kana_orig = $25;
    $12 = "カモシレ"$25; # 仮名形出現形

    #pron_orig = $14;
    $13 = "カモシレ"$14; # 発音形

    print_MeCab_entry();

    $1 = form_orig;
    #$2 = leftID_orig;
    #$15 = ortho_orig;
    #$25 = kana_orig;
    #$14 = pron_orig;
}

function gen_nakya(form, kana_pron) {
    form_orig = $1;
    $1 = form $1; # 出現形

    #leftID_orig = $2;
    #$2 = 912; # 左文脈ID：「ない」（助動詞，たまたま語末と同じ）に合わせる

    #ortho_orig = $15;
    $11 = "なければなら" $15; # 書字形基本形

    #kana_orig = $25;
    $12 = kana_pron $25; # 仮名形出現形

    #pron_orig = $14;
    $13 = kana_pron $14; # 発音形

    print_MeCab_entry();

    $1 = form_orig;
    #$2 = leftID_orig;
    #$15 = ortho_orig;
    #$25 = kana_orig;
    #$14 = pron_orig;
}

# 「ない」（助動詞）
$12~/^ない$/ {
    # 「かもしれない」
    gen_kamo("かもしれ");
    gen_kamo("かも知れ");
    gen_kamo("カモシレ");

    # 「なければならない」
    gen_nakya("なければなら", "ナケレバナラ");
    gen_nakya("ナケレバナラ", "ナケレバナラ");

    gen_nakya("なければいけ", "ナケレバイケ");
    gen_nakya("ナケレバイケ", "ナケレバイケ");

    gen_nakya("ないといけ", "ナイトイケ");
    gen_nakya("ナイトイケ", "ナイトイケ");

    gen_nakya("なきゃなら", "ナキャナラ");
    gen_nakya("ナキャナラ", "ナキャナラ");

    gen_nakya("なきゃいけ", "ナキャイケ");
    gen_nakya("ナキャイケ", "ナキャイケ");
}