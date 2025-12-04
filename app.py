import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定・デザイン調整（スマホ18:9 完全対応版）
# ---------------------------------------------------------

st.set_page_config(page_title="教科書在庫管理", layout="centered", initial_sidebar_state="collapsed")

# カスタムCSS：スマホの画面幅に絶対収めるための強力な設定
st.markdown("""
<style>
    /* 全体のリセットとフォント */
    body { font-family: "Helvetica Neue", Arial, sans-serif; color: #333; margin: 0; padding: 0; }
    
    /* ★重要：スマホの左右の余白を極限まで削る */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.2rem !important;
        padding-right: 0.2rem !important;
        max-width: 100% !important;
    }

    /* 検索バー周り */
    .control-panel {
        margin-bottom: 10px;
        padding: 0 5px;
    }
    div[data-testid="stTextInput"] { margin-bottom: 0px; }

    /* テーブルヘッダー（黒背景・白文字） */
    .table-header {
        background-color: #212529;
        color: #fff;
        padding: 6px 2px;
        font-weight: bold;
        font-size: 0.75rem; /* スマホ用に小さく */
        border-radius: 4px 4px 0 0;
        display: flex;
        align-items: center;
        margin-top: 5px;
    }
    
    /* 行のデザイン（強制1行・高さ固定） */
    .row-container {
        background-color: #fff;
        border-bottom: 1px solid #eee;
        border-left: 1px solid #eee;
        border-right: 1px solid #eee;
        padding: 4px 0;
        height: 45px; /* 高さを固定してガタつき防止 */
        display: flex;
        align-items: center;
        overflow: hidden; /* はみ出し防止 */
    }

    /* 教科書名の省略設定（これが重要） */
    .book-title {
        font-weight: bold;
        font-size: 0.85rem;
        white-space: nowrap;      /* 改行しない */
        overflow: hidden;         /* はみ出た部分は隠す */
        text-overflow: ellipsis;  /* ...にする */
        display: block;
        color: #333;
    }
    
    /* 在庫数と不足表示 */
    .stock-val { font-weight: bold; font-size: 0.9rem; text-align: center; display: block; }
    .text-alert { color: #e74c3c !important; } /* 朱色 */
    .badge-alert {
        font-size: 0.6rem;
        color: #e74c3c;
        font-weight: bold;
        display: block;
        line-height: 1;
    }

    /* Streamlitのレイアウト強制調整 */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important; /* 絶対に折り返さない */
        gap: 2px !important;          /* 隙間を最小に */
        align-items: center !important;
    }
    div[data-testid="column"] {
        min-width: 0 !important;      /* 幅の最小制限を解除 */
        flex: 1 1 auto !important;
        padding: 0 !important;
    }

    /* 数量入力欄の極小化 */
    div[data-testid="stNumberInput"] input {
        padding: 0 !important;
        height: 1.8rem !important;
        min-height: 1.8rem !important;
        font-size: 0.8rem !important;
        text-align: center !important;
    }
    div[data-testid="stNumberInput"] { margin: 0 !important; width: 100% !important; }
    button[kind="secondaryForm"] { display: none !important; }

    /* ボタンの極小化 */
    div[data-testid="column"] button {
        padding: 0 !important;
        height: 1.8rem !important;
        min-height: 1.8rem !important;
        font-size: 0.75rem !important;
        border-radius: 3px;
        border: none;
        width: 100%;
    }

    /* 色設定 */
    button[kind="secondary"] { background-color: #28a745 !important; color: white !important; } /* 緑 */
    button[kind="primary"] { background-color: #e74c3c !important; color: white !important; } /* 朱色 */
    div.stHorizontalBlock button[kind="secondary"] { /* 更新ボタンはグレー */
        background-color: #6c757d !important;
        border: 1px solid #ccc !important;
    }
    
    /* 不足時の行背景 */
    .bg-alert { background-color: #fff8f8; }

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

    # 操作パネル
    c_upd, c_src = st.columns([1.2, 3.8])
    with c_upd:
        if st.button("↻ 更新"): st.rerun()
    with c_src:
        search_query = st.text_input("src", placeholder="検索...", label_visibility="collapsed")

    # 並べ替え
    sort = st.radio("", ["追加日順", "在庫順"], horizontal=True, label_visibility="collapsed")
    if sort == "追加日順":
        if '商品ID' in df_items.columns: df_items = df_items.sort_values('商品ID', ascending=False)
    elif sort == "在庫順":
        df_items = df_items.sort_values('現在在庫数', ascending=True)

    if search_query:
        mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
        df = df_items[mask]
    else:
        df = df_items

    tab1, tab2 = st.tabs(["📦 在庫", "➕ 登録"])

    # ---------------------------------------------------------
    # 在庫リスト（絶対1行レイアウト）
    # ---------------------------------------------------------
    with tab1:
        # ヘッダー行
        st.markdown("""
        <div class="table-header">
            <div style="flex:4; padding-left:2px;">教科書名</div>
            <div style="flex:1; text-align:center;">在庫</div>
            <div style="flex:1.2; text-align:center;">数</div>
            <div style="flex:1.2; text-align:center;">入</div>
            <div style="flex:1.2; text-align:center;">出</div>
        </div>
        """, unsafe_allow_html=True)

        for i, row in df.iterrows():
            id_ = int(row['商品ID'])
            name = row['教科書名']
            stock = int(row['現在在庫数'])
            alert = int(row['発注点'])
            
            is_low = stock <= alert
            bg_cls = "bg-alert" if is_low else ""
            txt_cls = "text-alert" if is_low else ""
            alert_msg = '<span class="badge-alert">不足</span>' if is_low else ""

            # 行コンテナ開始
            st.markdown(f'<div class="row-container {bg_cls}">', unsafe_allow_html=True)
            
            # カラム比率：名前エリアを確保しつつ、他を最小限に
            c1, c2, c3, c4, c5 = st.columns([4, 1, 1.2, 1.2, 1.2], gap="small")
            
            with c1:
                # 教科書名（はみ出たら...になる）
                st.markdown(f'<span class="book-title" title="{name}">{name}</span>', unsafe_allow_html=True)
            
            with c2:
                # 在庫数と不足表示（朱色）
                st.markdown(f"""
                <div style="text-align:center; line-height:1;">
                    <span class="stock-val {txt_cls}">{stock}</span>
                    {alert_msg}
                </div>
                """, unsafe_allow_html=True)

            with c3:
                # 数量：初期値1固定
                qty = st.number_input("q", min_value=1, value=1, label_visibility="collapsed", key=f"q_{id_}")
                
            with c4:
                if st.button("入", key=f"in_{id_}"):
                    upd(ws_items, ws_logs, id_, name, stock, qty, "入庫")
            
            with c5:
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
        ws_l.append_row([int(new_log_id), str(now), str(type_), int(id_), int(change), str(name)])
    except:
        # 万が一のエラー時はID=1で記録トライ
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        ws_l.append_row([1, str(now), str(type_), int(id_), int(change), str(name)])

if __name__ == "__main__":
    main()
