import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定・デザイン調整
# ---------------------------------------------------------

st.set_page_config(page_title="教科書在庫管理", layout="centered", initial_sidebar_state="collapsed")

# カスタムCSS
st.markdown("""
<style>
    /* 1. 基本設定 */
    body { font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif; color: #333; margin: 0; padding: 0; }
    
    /* 2. 画面幅と余白の制御（PCは1/2、スマホは全幅） */
    .block-container { 
        padding-top: 4rem !important; /* タイトル見切れ防止のために広げる */
        padding-bottom: 5rem; 
        padding-left: 1rem !important; 
        padding-right: 1rem !important; 
    }
    
    /* PC画面用（幅を制限） */
    @media (min-width: 640px) {
        .block-container {
            max-width: 700px !important; /* 画面の約1/2 */
            margin: 0 auto !important;
        }
    }
    /* スマホ画面用（幅いっぱい） */
    @media (max-width: 640px) {
        .block-container {
            max-width: 100% !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
    }

    /* 3. タイトルの調整 */
    h3 { 
        font-size: 1.5rem !important; 
        margin-bottom: 1rem; 
        font-weight: bold;
    }

    /* 4. 入力欄・ボタンの共通設定 */
    div[data-testid="stNumberInput"] input {
        text-align: center !important;
    }
    div[data-testid="stTextInput"] { margin-bottom: 0px; }

    /* 5. ヘッダーのデザイン（黒背景） */
    .table-header {
        background-color: #222;
        color: white;
        padding: 8px 5px;
        font-weight: bold;
        font-size: 12px;
        text-align: center;
        border-radius: 4px 4px 0 0;
        display: flex;
        align-items: center;
        margin-top: 10px;
        width: 100%;
    }

    /* 6. 行のデザイン（枠線あり） */
    .row-container {
        border-bottom: 1px solid #ccc;
        border-left: 1px solid #ccc;
        border-right: 1px solid #ccc;
        padding: 8px 5px;
        background-color: #fff;
        display: flex;
        align-items: center;
        width: 100%;
    }

    /* 7. 操作パネルのボタンデザイン */
    /* 通常時（選択済み）のスタイルはPython側で type="primary/secondary" で指定 */
    /* ここでは共通スタイルを定義 */
    div.stButton > button {
        font-weight: bold !important;
        border-radius: 6px !important;
        height: 45px !important; /* 押しやすく大きく */
        width: 100% !important;
    }

    /* 入庫ボタン（緑） */
    button[kind="secondary"] {
        color: #28a745 !important;
        border: 2px solid #28a745 !important;
        background: white !important;
    }
    button[kind="secondary"]:hover, button[kind="secondary"]:active {
        background-color: #e6f9e6 !important;
    }

    /* 出庫ボタン（朱色） */
    button[kind="primary"] {
        color: #e74c3c !important;
        border: 2px solid #e74c3c !important;
        background: white !important;
    }
    button[kind="primary"]:hover, button[kind="primary"]:active {
        background-color: #fceceb !important;
    }
    
    /* 無効状態（未選択時）のボタン：白黒グレー */
    button:disabled {
        border-color: #ccc !important;
        color: #999 !important;
        background-color: #f0f0f0 !important;
        opacity: 0.7;
    }

    /* 文字スタイル */
    .book-name { font-size: 14px; font-weight: bold; line-height: 1.2; text-align: left; }
    .book-sub { font-size: 10px; color: #666; display: block; text-align: left; }
    .stock-val { font-size: 14px; font-weight: bold; text-align: center; }
    
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
    except Exception as e:
        st.error(f"接続エラー: {e}")
        return None, None, None, None, None

def main():
    st.markdown("### 教科書在庫管理")
    
    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None: return

    # データ前処理
    df_items.columns = df_items.columns.str.strip()
    cols_to_num = ['商品ID', '現在在庫数', '発注点']
    for col in cols_to_num:
        if col in df_items.columns:
            df_items[col] = pd.to_numeric(df_items[col], errors='coerce').fillna(0).astype(int)

    # 検索・更新エリア
    c_search, c_update = st.columns([3, 1])
    with c_search:
        search_query = st.text_input("search", placeholder="検索...", label_visibility="collapsed")
    with c_update:
        if st.button("↻ 更新"): st.rerun()

    # 並べ替え
    sort_mode = st.radio("", ["追加日順", "在庫少ない順"], horizontal=True, label_visibility="collapsed")
    
    if sort_mode == "追加日順":
        if '商品ID' in df_items.columns: df_items = df_items.sort_values('商品ID', ascending=False)
    elif sort_mode == "在庫少ない順":
        df_items = df_items.sort_values('現在在庫数', ascending=True)

    if search_query:
        mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
        df_display = df_items[mask]
    else:
        df_display = df_items

    tab_list, tab_add = st.tabs(["在庫リスト", "⊕教科書を追加"])

    # ---------------------------------------------------------
    # 在庫リスト（操作パネル分離型）
    # ---------------------------------------------------------
    with tab_list:
        
        # --- 1. 操作パネル（常時表示・選択式） ---
        st.markdown("---")
        st.caption("▼ 操作する教科書を選択してください")
        
        # 教科書選択プルダウン（名前と在庫を表示）
        # IDをキーにして一意に特定
        options = {f"{row['教科書名']} (在庫: {row['現在在庫数']})": row['商品ID'] for index, row in df_display.iterrows()}
        selected_label = st.selectbox("教科書選択", options=list(options.keys()), index=None, placeholder="教科書をタップして選択...", label_visibility="collapsed")
        
        selected_id = options[selected_label] if selected_label else None
        
        # 操作ボタンエリア
        c_qty, c_in, c_out = st.columns([1, 1, 1], gap="small")
        
        with c_qty:
            # 数量選択（初期値1）
            qty = st.number_input("数量", min_value=1, value=1, key="panel_qty")
            
        with c_in:
            # 入庫ボタン（選択なし時は無効化 disabled=True）
            # disabled=TrueにするとStreamlitが自動でグレーアウトします
            if st.button("入庫", key="panel_in", type="secondary", disabled=(selected_id is None), use_container_width=True):
                if selected_id:
                    # 最新の在庫数を取得して更新
                    current_row = df_items[df_items['商品ID'] == selected_id].iloc[0]
                    update_stock(ws_items, ws_logs, selected_id, current_row['教科書名'], int(current_row['現在在庫数']), qty, "入庫")

        with c_out:
            # 出庫ボタン（選択なし時は無効化）
            if st.button("出庫", key="panel_out", type="primary", disabled=(selected_id is None), use_container_width=True):
                if selected_id:
                    current_row = df_items[df_items['商品ID'] == selected_id].iloc[0]
                    update_stock(ws_items, ws_logs, selected_id, current_row['教科書名'], int(current_row['現在在庫数']), qty, "出庫")

        st.markdown("---")

        # --- 2. 在庫一覧（閲覧専用） ---
        # ヘッダー行
        st.markdown("""
        <div class="table-header">
            <div style="flex:4; text-align:left; padding-left:5px;">教科書名</div>
            <div style="flex:1.5; text-align:center;">在庫</div>
            <div style="flex:1.5; text-align:center;">発注点</div>
        </div>
        """, unsafe_allow_html=True)

        if df_display.empty:
            st.info("データなし")
        
        for index, row in df_display.iterrows():
            name = row['教科書名']
            stock = int(row['現在在庫数'])
            alert = int(row['発注点'])
            pub = row['出版社']
            
            is_low = stock <= alert
            bg_style = "background-color: #fff5f5;" if is_low else "background-color: #fff;"
            stock_color = "#d63031" if is_low else "#333"
            alert_badge = '<span style="color:red; font-size:9px;">不足</span>' if is_low else ""

            # 行コンテナ
            st.markdown(f'<div class="row-container" style="{bg_style}">', unsafe_allow_html=True)
            
            # カラム（ボタンがないのでスッキリ）
            c1, c2, c3 = st.columns([4, 1.5, 1.5])
            
            with c1:
                st.markdown(f"""
                <div style="line-height:1.1;">
                    <div class="book-name">{name}</div>
                    <div class="book-sub">{pub}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with c2:
                st.markdown(f"""
                <div style="text-align:center;">
                    <span class="stock-val" style="color:{stock_color};">{stock}</span>
                    {alert_badge}
                </div>
                """, unsafe_allow_html=True)
                
            with c3:
                st.markdown(f'<div style="text-align:center; font-size:12px;">{alert}</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 新規登録
    # ---------------------------------------------------------
    with tab_add:
        st.markdown("##### 新規登録")
        with st.form("add"):
            names = list(df_items['教科書名'].unique()) if '教科書名' in df_items.columns else []
            name_sel = st.selectbox("教科書名", options=names + ["新規入力"], index=None, placeholder="選択...")
            name_in = ""
            if name_sel == "新規入力": name_in = st.text_input("入力")
            
            pubs = list(df_items['出版社'].unique()) if '出版社' in df_items.columns else []
            pub_sel = st.selectbox("出版社", options=pubs + ["その他"], index=None, placeholder="選択...")
            pub_in = ""
            if pub_sel == "その他": pub_in = st.text_input("入力")
            
            c1, c2 = st.columns(2)
            isbn = c1.text_input("ISBN")
            loc = c2.text_input("保管場所")
            
            c3, c4 = st.columns(2)
            stock = c3.number_input("初期在庫", min_value=1, value=1)
            alert = c4.number_input("発注点", min_value=1, value=1)
            
            if st.form_submit_button("登録", use_container_width=True):
                fname = name_in if name_sel == "新規入力" else name_sel
                fpub = pub_in if pub_sel == "その他" else pub_sel
                
                if not fname or not fpub:
                    st.error("必須項目不足")
                else:
                    nid = int(df_items['商品ID'].max()) + 1 if not df_items.empty else 1
                    ws_items.append_row([int(nid), str(fname), str(isbn), str(fpub), int(stock), int(alert), str(loc)])
                    add_log(ws_logs, "新規登録", nid, fname, stock)
                    st.success(f"登録: {fname}")
                    st.rerun()

# ---------------------------------------------------------
# ログ記録
# ---------------------------------------------------------
def update_stock(ws_items, ws_logs, item_id, item_name, current_stock, quantity, action_type):
    new_stock = current_stock + quantity if action_type == "入庫" else current_stock - quantity
    if new_stock < 0:
        st.error("在庫不足")
        return
    try:
        cell = ws_items.find(str(item_id), in_column=1)
        ws_items.update_cell(cell.row, 5, new_stock)
        
        change = quantity if action_type == "入庫" else -quantity
        add_log(ws_logs, action_type, item_id, item_name, change)
        
        st.toast(f"{action_type}完了 (残{new_stock})")
        st.rerun()
    except Exception as e:
        st.error(f"エラー: {e}")

def add_log(ws_logs, action_type, item_id, item_name, change_val):
    try:
        log_id = int(datetime.now().timestamp())
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        ws_logs.append_row([log_id, now, action_type, int(item_id), int(change_val), str(item_name)])
    except:
        pass 

if __name__ == "__main__":
    main()
