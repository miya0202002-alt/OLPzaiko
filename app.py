import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定・デザイン調整（スマホ幅完全固定・縦線区切り版）
# ---------------------------------------------------------

st.set_page_config(page_title="教科書在庫管理", layout="centered", initial_sidebar_state="collapsed")

# カスタムCSS：幅を％で完全固定し、縦線を入れる設定
st.markdown("""
<style>
    /* リセット */
    body { font-family: "Helvetica Neue", Arial, sans-serif; color: #333; margin: 0; padding: 0; }
    
    /* コンテナの余白を削除して画面いっぱい使う */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.2rem !important;
        padding-right: 0.2rem !important;
        max-width: 100% !important;
    }

    /* Streamlitのカラム設定を強制上書き（隙間ゼロ・折り返しなし） */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0 !important; /* 隙間なし */
        align-items: stretch !important; /* 高さを揃える */
    }
    
    /* カラムごとの幅定義（合計100%になるように配分） */
    /* 1列目：教科書情報 (40%) */
    div[data-testid="column"]:nth-of-type(1) {
        flex: 0 0 40% !important;
        max-width: 40% !important;
        min-width: 0 !important;
        border-right: 1px solid #e0e0e0; /* 縦線 */
    }
    /* 2列目：在庫 (15%) */
    div[data-testid="column"]:nth-of-type(2) {
        flex: 0 0 15% !important;
        max-width: 15% !important;
        min-width: 0 !important;
        border-right: 1px solid #e0e0e0;
    }
    /* 3列目：数量 (15%) */
    div[data-testid="column"]:nth-of-type(3) {
        flex: 0 0 15% !important;
        max-width: 15% !important;
        min-width: 0 !important;
        border-right: 1px solid #e0e0e0;
    }
    /* 4列目：入庫 (15%) */
    div[data-testid="column"]:nth-of-type(4) {
        flex: 0 0 15% !important;
        max-width: 15% !important;
        min-width: 0 !important;
        border-right: 1px solid #e0e0e0;
    }
    /* 5列目：出庫 (15%) */
    div[data-testid="column"]:nth-of-type(5) {
        flex: 0 0 15% !important;
        max-width: 15% !important;
        min-width: 0 !important;
    }

    /* 各カラムの中身の余白調整 */
    div[data-testid="column"] > div {
        padding: 0 2px !important;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    /* ヘッダー（黒背景）のスタイル（カラム幅と合わせる） */
    .header-row {
        display: flex;
        background-color: #222;
        color: white;
        font-weight: bold;
        font-size: 0.75rem;
        border-radius: 4px 4px 0 0;
        overflow: hidden;
    }
    .h-col {
        padding: 8px 2px;
        text-align: center;
        border-right: 1px solid #444; /* ヘッダー内の縦線 */
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .h-col:last-child { border-right: none; }
    
    /* 1行ごとの枠線 */
    .row-wrapper {
        border-bottom: 1px solid #e0e0e0;
        border-left: 1px solid #e0e0e0;
        border-right: 1px solid #e0e0e0;
        background-color: #fff;
    }

    /* 教科書名の表示調整 */
    .book-name {
        font-weight: bold;
        font-size: 0.8rem;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
    }
    .book-sub { font-size: 0.65rem; color: #666; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

    /* 入力欄とボタンの極小化 */
    div[data-testid="stNumberInput"] input {
        padding: 0 !important;
        height: 2.0em !important;
        font-size: 0.9em !important;
        text-align: center !important;
    }
    div[data-testid="column"] button {
        padding: 0 !important;
        height: 2.0em !important;
        font-size: 0.8em !important;
        width: 100%;
        border-radius: 2px;
    }
    
    /* 色設定 */
    button[kind="secondary"] { background-color: #28a745 !important; color: white !important; border: none !important; }
    button[kind="primary"] { background-color: #e74c3c !important; color: white !important; border: none !important; }
    
    /* アラート */
    .bg-alert { background-color: #fff5f5 !important; }
    .text-alert { color: #e74c3c; font-weight: bold; }
    
</style>
""", unsafe_allow_html=True)

JSON_FILE = 'secret_key.json' 
SPREADSHEET_NAME = '在庫管理システム'

@st.cache_resource
def get_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    if "gcp_service_account" in st.secrets:
        key_dict = json.loads(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
    client = gspread.authorize(creds)
    return client

def load_data():
    client = get_connection()
    try:
        sh = client.open(SPREADSHEET_NAME)
        ws_items = sh.worksheet('商品マスタ')
        items_data = ws_items.get_all_values()
        if not items_data: return None, None, pd.DataFrame(), None, pd.DataFrame()
        df_items = pd.DataFrame(items_data[1:], columns=items_data[0])
        ws_logs = sh.worksheet('入出庫履歴')
        logs_data = ws_logs.get_all_values()
        if not logs_data:
            df_logs = pd.DataFrame(columns=['ログID', '日時', '操作', '商品ID', '変動数', '備考'])
        else:
            df_logs = pd.DataFrame(logs_data[1:], columns=logs_data[0])
        return sh, ws_items, df_items, ws_logs, df_logs
    except: return None, None, None, None, None

def main():
    st.markdown("<h5>📚 教科書在庫管理</h5>", unsafe_allow_html=True)
    
    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None: return

    # データ処理
    df_items.columns = df_items.columns.str.strip()
    for col in ['商品ID', '現在在庫数', '発注点']:
        if col in df_items.columns:
            df_items[col] = pd.to_numeric(df_items[col], errors='coerce').fillna(0).astype(int)

    # 検索・更新・並べ替え
    c_search, c_upd = st.columns([4, 1]) # ここは標準の幅設定を使用（下のCSSはテーブル部分のみに効くように設計）
    with c_search:
        search_query = st.text_input("src", placeholder="検索...", label_visibility="collapsed")
    with c_upd:
        if st.button("↻"): st.rerun()

    sort = st.radio("", ["追加日順", "在庫順"], horizontal=True, label_visibility="collapsed")
    if sort == "追加日順":
        if '商品ID' in df_items.columns: df_items = df_items.sort_values('商品ID', ascending=False)
    elif sort == "在庫順":
        df_items = df_items.sort_values('現在在庫数', ascending=True)

    if search_query:
        mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
        df_display = df_items[mask]
    else:
        df_display = df_items

    # タブ名変更
    tab1, tab2 = st.tabs(["在庫", "⊕教科書を追加"])

    # ---------------------------------------------------------
    # 在庫タブ（縦線あり・完全幅固定）
    # ---------------------------------------------------------
    with tab1:
        # ヘッダー（黒背景・縦線あり）
        # CSSのパーセンテージと完全に一致させる (40%, 15%, 15%, 15%, 15%)
        st.markdown("""
        <div class="header-row">
            <div class="h-col" style="flex:0 0 40%;">教科書情報</div>
            <div class="h-col" style="flex:0 0 15%;">在庫</div>
            <div class="h-col" style="flex:0 0 15%;">数</div>
            <div class="h-col" style="flex:0 0 15%;">入庫</div>
            <div class="h-col" style="flex:0 0 15%;">出庫</div>
        </div>
        """, unsafe_allow_html=True)

        for i, row in df_display.iterrows():
            id_ = int(row['商品ID'])
            name = row['教科書名']
            stock = int(row['現在在庫数'])
            alert = int(row['発注点'])
            pub = row['出版社']
            
            is_low = stock <= alert
            bg_cls = "bg-alert" if is_low else ""
            stock_cls = "text-alert" if is_low else ""

            # 行のラッパー開始
            st.markdown(f'<div class="row-wrapper {bg_cls}">', unsafe_allow_html=True)
            
            # カラム（CSSで幅を強制制御しているので、ここでの比率は無視されるが念のため記述）
            c1, c2, c3, c4, c5 = st.columns(5)
            
            with c1: # 教科書情報 (40%)
                st.markdown(f"""
                <div style="padding-left:4px; overflow:hidden;">
                    <span class="book-name" title="{name}">{name}</span>
                    <span class="book-sub">{pub}</span>
                </div>
                """, unsafe_allow_html=True)
            
            with c2: # 在庫 (15%)
                st.markdown(f"""
                <div style="text-align:center;">
                    <span style="font-weight:bold; {stock_cls}">{stock}</span>
                </div>
                """, unsafe_allow_html=True)

            with c3: # 数 (15%)
                qty = st.number_input("q", min_value=1, value=1, label_visibility="collapsed", key=f"q_{id_}")
                
            with c4: # 入庫 (15%)
                if st.button("入", key=f"in_{id_}"):
                    upd(ws_items, ws_logs, id_, name, stock, qty, "入庫")
            
            with c5: # 出庫 (15%)
                if st.button("出", key=f"out_{id_}", type="primary"):
                    upd(ws_items, ws_logs, id_, name, stock, qty, "出庫")

            st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 新規登録
    # ---------------------------------------------------------
    with tab2:
        with st.form("add"):
            exist_n = list(df_items['教科書名'].unique()) if '教科書名' in df_items.columns else []
            n_sel = st.selectbox("教科書名", options=exist_n+["新規"], index=None, placeholder="選択...")
            n_inp = ""
            if n_sel == "新規": n_inp = st.text_input("名称入力")
            
            exist_p = list(df_items['出版社'].unique()) if '出版社' in df_items.columns else []
            p_sel = st.selectbox("出版社", options=exist_p+["その他"], index=None, placeholder="選択...")
            p_inp = ""
            if p_sel == "その他": p_inp = st.text_input("出版社入力")
            
            c_a, c_b = st.columns(2)
            isbn = c_a.text_input("ISBN")
            loc = c_b.text_input("保管")
            
            c_c, c_d = st.columns(2)
            # 初期値1
            stock = c_c.number_input("初期在庫", min_value=1, value=1)
            alert = c_d.number_input("発注点", min_value=1, value=1)
            
            if st.form_submit_button("登録", use_container_width=True):
                fin_n = n_inp if n_sel == "新規" else n_sel
                fin_p = p_inp if p_sel == "その他" else p_sel
                if not fin_n or not fin_p: st.error("必須項目不足")
                else:
                    new_id = int(df_items['商品ID'].max())+1 if not df_items.empty else 1
                    ws_items.append_row([new_id, str(fin_n), str(isbn), str(fin_p), int(stock), int(alert), str(loc)])
                    add_log(ws_logs, "新規登録", new_id, fin_n, stock)
                    st.success("登録完了")
                    st.rerun()

def upd(ws_i, ws_l, id_, name, curr, qty, type_):
    new = curr + qty if type_ == "入庫" else curr - qty
    if new < 0:
        st.error("在庫不足")
        return
    try:
        cell = ws_i.find(str(id_), in_column=1)
        ws_i.update_cell(cell.row, 5, new)
        change = qty if type_ == "入庫" else -qty
        add_log(ws_l, type_, id_, name, change)
        st.toast(f"{type_}完了")
        st.rerun()
    except: st.error("エラー")

def add_log(ws_l, type_, id_, name, change):
    try:
        vals = ws_l.col_values(1)
        new_id = int(vals[-1])+1 if len(vals)>1 and str(vals[-1]).isdigit() else 1
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        ws_l.append_row([int(new_id), str(now), str(type_), int(id_), int(change), str(name)])
    except:
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        ws_l.append_row([1, str(now), str(type_), int(id_), int(change), str(name)])

if __name__ == "__main__":
    main()
