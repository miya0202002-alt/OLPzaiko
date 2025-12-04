import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定・デザイン調整（スマホ完全対応・強制横並び版）
# ---------------------------------------------------------

st.set_page_config(page_title="教科書在庫管理", layout="centered", initial_sidebar_state="collapsed")

# カスタムCSS
st.markdown("""
<style>
    /* 全体の調整 */
    body { font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif; color: #333; margin: 0; padding: 0; }
    
    /* 上部の文字見切れ防止 */
    .block-container { padding-top: 2rem; padding-bottom: 5rem; padding-left: 0.5rem; padding-right: 0.5rem; }
    
    /* ★最重要：スマホでもカラムを縦積みにせず、強制的に横並びにする設定 */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 2px !important;
    }
    
    /* 各カラムの幅を強制的に調整（はみ出し防止） */
    div[data-testid="column"] {
        min-width: 0px !important; /* これがないとスマホで崩れる */
        flex: 1 1 auto !important;
        padding: 0 !important;
    }

    /* 検索バー周りの調整 */
    div[data-testid="stTextInput"] { margin-bottom: 10px; }
    
    /* テーブルヘッダー（GAS風 黒背景） */
    .table-header {
        background-color: #222;
        color: #fff;
        padding: 8px 2px;
        font-weight: bold;
        font-size: 0.8em;
        border-radius: 4px 4px 0 0;
        margin-top: 5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* 1行レイアウトのスタイル */
    .row-container {
        border-bottom: 1px solid #ddd;
        border-left: 1px solid #ddd;
        border-right: 1px solid #ddd;
        padding: 5px 0;
        background-color: #fff;
        margin-bottom: -1px; /* 線を重ねて太くなるのを防ぐ */
    }
    
    /* 教科書名のスタイル（線が被らないようにパディング調整） */
    .book-info {
        padding-left: 5px;
        line-height: 1.1;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis; /* 長すぎる場合は...にする */
    }
    .text-title { font-size: 0.9em; font-weight: bold; color: #000; }
    .text-sub { font-size: 0.7em; color: #888; }
    
    /* 在庫数表示 */
    .stock-display { text-align: center; font-weight: bold; font-size: 1.1em; }
    
    /* 入力欄（数量）の強制小型化 */
    div[data-testid="stNumberInput"] { margin: 0 !important; width: 100% !important; }
    div[data-testid="stNumberInput"] input {
        padding: 0 !important;
        height: 2.0em !important;
        min-height: 2.0em !important;
        text-align: center !important;
        font-size: 0.9em !important;
        width: 100% !important;
    }
    /* 上下の＋－ボタンを消してスッキリさせる（お好みで削除可） */
    button[kind="secondaryForm"] { display: none !important; } 

    /* ボタンのデザイン調整 */
    div.stButton > button {
        padding: 0 !important;
        min-height: 2.0em !important;
        height: 2.0em !important;
        font-size: 0.85em !important;
        border-radius: 4px;
        border: none;
        width: 100%;
    }
    
    /* ★入庫の「入」ボタンを緑にする設定 */
    /* 入庫ボタン（行内の左側のボタン）を特定するためのクラス */
    .btn-green button {
        background-color: #28a745 !important;
        color: white !important;
    }
    
    /* 出庫の「出」ボタンを朱色にする */
    .btn-red button {
        background-color: #e74c3c !important;
        color: white !important;
    }

    /* アラート表示 */
    .bg-alert { background-color: #fff5f5; }
    .text-alert { color: #d63031; }
    
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

    # 検索・更新・並べ替え
    c_search, c_update = st.columns([3, 1])
    with c_search:
        search_query = st.text_input("検索", placeholder="教科書名...", label_visibility="collapsed")
    with c_update:
        if st.button("↻"): st.rerun()

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

    tab_list, tab_add = st.tabs(["在庫リスト", "➕ 新規登録"])

    # ---------------------------------------------------------
    # 在庫リスト（強制横並び版）
    # ---------------------------------------------------------
    with tab_list:
        # ヘッダー行（Flexboxで比率調整）
        st.markdown("""
        <div class="table-header">
            <div style="flex:3.5; padding-left:5px;">教科書情報</div>
            <div style="flex:1; text-align:center;">在庫</div>
            <div style="flex:1.2; text-align:center;">数</div>
            <div style="flex:1; text-align:center;">入</div>
            <div style="flex:1; text-align:center;">出</div>
        </div>
        """, unsafe_allow_html=True)

        if df_display.empty:
            st.info("データがありません")
        
        for index, row in df_display.iterrows():
            item_id = int(row['商品ID'])
            name = row['教科書名']
            stock = int(row['現在在庫数'])
            alert = int(row['発注点'])
            pub = row['出版社']
            
            is_low = stock <= alert
            bg_style = "bg-alert" if is_low else ""
            stock_color = "text-alert" if is_low else ""

            # 行の開始
            st.markdown(f'<div class="row-container {bg_style}">', unsafe_allow_html=True)
            
            # ★ここがポイント：比率を調整して教科書名を狭く(3.5)、ボタン類を確保
            # gap="2px" で限界まで詰める
            c1, c2, c3, c4, c5 = st.columns([3.5, 1, 1.2, 1, 1], gap="small")
            
            with c1:
                st.markdown(f"""
                <div class="book-info">
                    <div class="text-title">{name}</div>
                    <div class="text-sub">{pub}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                st.markdown(f'<div class="stock-display {stock_color}">{stock}</div>', unsafe_allow_html=True)

            with c3:
                # 数量入力：ラベルなし、初期値1
                qty = st.number_input("q", min_value=1, value=1, label_visibility="collapsed", key=f"q_{item_id}")
                
            with c4:
                # 入庫（クラス btn-green を適用するために div で囲むハックはStreamlitでは難しいので、
                # keyを使ってCSSで狙い撃ちするか、st.markdownでボタンを作るのは機能しないため、
                # 諦めてここでは標準ボタンを配置し、上のCSSで強制的に色を変える）
                st.markdown('<span class="btn-green">', unsafe_allow_html=True)
                if st.button("入", key=f"in_{item_id}"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "入庫")
                st.markdown('</span>', unsafe_allow_html=True)
            
            with c5:
                # 出庫
                st.markdown('<span class="btn-red">', unsafe_allow_html=True)
                if st.button("出", key=f"out_{item_id}"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "出庫")
                st.markdown('</span>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 新規登録
    # ---------------------------------------------------------
    with tab_add:
        st.markdown("##### 新しい教科書の登録")
        with st.form("add"):
            existing_names = list(df_items['教科書名'].unique()) if '教科書名' in df_items.columns else []
            name_select = st.selectbox("教科書名", options=existing_names + ["新規入力"], index=None, placeholder="教科書名を選択...")
            name_input = ""
            if name_select == "新規入力":
                name_input = st.text_input("新しい教科書名を入力")
            
            existing_pubs = list(df_items['出版社'].unique()) if '出版社' in df_items.columns else []
            pub_select = st.selectbox("出版社", options=existing_pubs + ["その他"], index=None, placeholder="出版社を選択...")
            pub_input = ""
            if pub_select == "その他":
                pub_input = st.text_input("出版社名を入力")
                
            c1, c2 = st.columns(2)
            isbn = c1.text_input("ISBN")
            loc = c2.text_input("保管場所")
            
            c3, c4 = st.columns(2)
            # 初期値「1」
            stock = c3.number_input("初期在庫 *", min_value=1, value=1)
            alert = c4.number_input("発注点", min_value=1, value=1)
            
            if st.form_submit_button("登録", use_container_width=True):
                final_name = name_input if name_select == "新規入力" else name_select
                final_pub = pub_input if pub_select == "その他" else pub_select
                
                if not final_name or not final_pub:
                    st.error("教科書名と出版社は必須です")
                else:
                    new_id = int(df_items['商品ID'].max()) + 1 if not df_items.empty else 1
                    new_row = [int(new_id), str(final_name), str(isbn), str(final_pub), int(stock), int(alert), str(loc)]
                    ws_items.append_row(new_row)
                    add_log(ws_logs, "新規登録", new_id, final_name, stock)
                    st.success(f"「{final_name}」を登録しました")
                    st.rerun()

def update_stock(ws_items, ws_logs, item_id, item_name, current_stock, quantity, action_type):
    new_stock = current_stock + quantity if action_type == "入庫" else current_stock - quantity
    if new_stock < 0:
        st.error("在庫が足りません")
        return
    try:
        cell = ws_items.find(str(item_id), in_column=1)
        ws_items.update_cell(cell.row, 5, new_stock)
        
        change = quantity if action_type == "入庫" else -quantity
        add_log(ws_logs, action_type, item_id, item_name, change)
        
        st.toast(f"{action_type}完了！ (現在: {new_stock}冊)")
        st.rerun()
    except Exception as e:
        st.error(f"エラー: {e}")

def add_log(ws_logs, action_type, item_id, item_name, change_val):
    try:
        all_vals = ws_logs.col_values(1)
        if len(all_vals) > 1:
            last_id = all_vals[-1]
            new_log_id = int(last_id) + 1 if str(last_id).isdigit() else 1
        else:
            new_log_id = 1
        now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        row_data = [int(new_log_id), str(now), str(action_type), int(item_id), int(change_val), str(item_name)]
        ws_logs.append_row(row_data)
    except Exception as e:
        st.error(f"ログ記録エラー: {e}")

if __name__ == "__main__":
    main()
