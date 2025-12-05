import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定
# ---------------------------------------------------------
st.set_page_config(page_title="教科書在庫管理", layout="centered", initial_sidebar_state="expanded")

# ---------------------------------------------------------
# CSS (スマホ完全対応・ヘッダー文字縮小版)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* 1. 全体設定 */
    body { font-family: -apple-system, sans-serif; color: #333; margin: 0; padding: 0; }
    
    /* 画面の余白を極限まで削る */
    .block-container { 
        padding-top: 3.5rem !important; 
        padding-bottom: 100px !important; 
        padding-left: 0.1rem !important; 
        padding-right: 0.1rem !important; 
        max-width: 100% !important;
    }

    /* PC画面用設定 */
    @media (min-width: 640px) {
        .block-container {
            max-width: 600px !important;
            margin: 0 auto !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        section[data-testid="stSidebar"] {
            width: 600px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
        }
    }

    /* 2. タイトル */
    h3 { 
        font-size: 1.4rem !important; 
        margin-bottom: 0.5rem; 
        font-weight: 900; 
        padding-left: 0.5rem;
    }

    /* 3. 強制横並び */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 1px !important;
        align-items: center !important;
        width: 100% !important;
    }
    div[data-testid="column"] {
        min-width: 0px !important;
        padding: 0 1px !important;
        overflow: hidden !important;
        flex: 1 1 auto !important;
    }

    /* 4. 下部固定パネル */
    section[data-testid="stSidebar"] {
        position: fixed !important;
        bottom: 0 !important;
        top: auto !important;
        left: 0 !important;
        height: auto !important;
        min-height: 0 !important;
        background-color: #fcfcfc !important;
        border-top: 1px solid #ddd !important;
        box-shadow: 0 -4px 6px rgba(0,0,0,0.05) !important;
        z-index: 999999 !important;
        padding: 0 !important;
    }
    
    section[data-testid="stSidebar"] .block-container {
        padding: 8px 5px 15px 5px !important;
        margin: 0 !important;
        overflow: hidden !important;
    }
    
    /* 不要パーツ削除 */
    div[data-testid="stSidebarNav"], 
    button[kind="header"],
    div[data-testid="collapsedControl"], 
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarUserContent"] > div:first-child { 
        display: none !important; 
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
    }

    /* 5. ヘッダーのデザイン（★文字を小さく修正！） */
    .header-box {
        background-color: #222;
        color: white;
        font-weight: bold;
        font-size: 10px !important; /* ★小さく */
        text-align: center;
        padding: 4px 0 !important;  /* ★余白削減 */
        border-radius: 3px;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        line-height: 1.1;
        width: 100%;
    }

    /* リスト内のボタン */
    div.row-btn button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #333 !important;
        text-align: left !important;
        font-weight: bold !important;
        font-size: 13px !important; /* 少し小さくして収まりよく */
        padding: 4px 0 !important;
        white-space: normal !important;
        line-height: 1.2 !important;
        width: 100% !important;
        display: block !important;
        height: auto !important;
        min-height: auto !important;
    }
    div.row-btn button:active, div.row-btn button:focus {
        background-color: #f0f0f0 !important;
        color: #000 !important;
    }

    /* 6. フッター内のボタン・入力欄 */
    .footer-btn button {
        height: 36px !important;
        font-size: 12px !important;
        font-weight: bold !important;
        border-radius: 4px !important;
        padding: 0 !important;
    }
    div[data-testid="stNumberInput"] input {
        height: 36px !important;
        text-align: center !important;
        font-size: 14px !important;
        padding: 0 !important;
    }
    div[data-testid="stNumberInput"] { margin: 0 !important; }

    /* 色設定 */
    .btn-in button { 
        background-color: white !important; 
        color: #28a745 !important; 
        border: 2px solid #28a745 !important; 
    }
    .btn-out button { 
        background-color: white !important; 
        color: #e74c3c !important; 
        border: 2px solid #e74c3c !important; 
    }
    
    button:disabled {
        border-color: #ddd !important;
        color: #ccc !important;
        background-color: white !important;
    }

    /* 区切り線 */
    hr { margin: 0 !important; border-top: 1px solid #eee !important; }

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
    if 'selected_book_id' not in st.session_state:
        st.session_state.selected_book_id = None
        st.session_state.selected_book_name = "（未選択）"
        st.session_state.selected_book_stock = 0

    st.markdown("### 教科書在庫管理")
    
    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None: return

    df_items.columns = df_items.columns.str.strip()
    cols_to_num = ['商品ID', '現在在庫数', '発注点']
    for col in cols_to_num:
        if col in df_items.columns:
            df_items[col] = pd.to_numeric(df_items[col], errors='coerce').fillna(0).astype(int)

    # 検索・更新
    c_search, c_update = st.columns([3.5, 1])
    with c_search:
        search_query = st.text_input("search", placeholder="検索...", label_visibility="collapsed")
    with c_update:
        if st.button("↻ 更新"): 
            st.session_state.selected_book_id = None
            st.rerun()

    tab_list, tab_add = st.tabs(["在庫リスト", "⊕教科書を追加"])

    # ---------------------------------------------------------
    # 在庫リスト
    # ---------------------------------------------------------
    with tab_list:
        if search_query:
            mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
            df_display = df_items[mask]
        else:
            df_display = df_items

        # ヘッダー行（余白削減）
        h1, h2 = st.columns([4, 1.5])
        h1.markdown('<div class="header-box" style="justify-content:flex-start; padding-left:5px;">教科書名（タップして選択）</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-box">在庫</div>', unsafe_allow_html=True)

        for index, row in df_display.iterrows():
            item_id = int(row['商品ID'])
            name = row['教科書名']
            stock = int(row['現在在庫数'])
            alert = int(row['発注点'])
            
            is_low = stock <= alert
            stock_color = "#e74c3c" if is_low else "#333"
            
            # データ行
            c1, c2 = st.columns([4, 1.5])
            
            with c1:
                st.markdown('<div class="row-btn">', unsafe_allow_html=True)
                label = f"{name}"
                if st.button(label, key=f"sel_{item_id}", use_container_width=True):
                    st.session_state.selected_book_id = item_id
                    st.session_state.selected_book_name = name
                    st.session_state.selected_book_stock = stock
                st.markdown('</div>', unsafe_allow_html=True)
            
            with c2:
                st.markdown(f"""
                <div style="text-align:center; height:100%; display:flex; align-items:center; justify-content:center;">
                    <span style="font-size:16px; font-weight:bold; color:{stock_color};">{stock}</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 下部固定操作パネル
    # ---------------------------------------------------------
    with st.sidebar:
        display_name = st.session_state.selected_book_name
        if st.session_state.selected_book_id is None:
            display_name = "（リストから教科書を選択してください）"
            
        st.markdown(f"<div style='font-size:11px; color:#555; margin-bottom:2px;'>選択中: <b>{display_name}</b></div>", unsafe_allow_html=True)
        
        c_qty, c_in, c_out = st.columns([1.2, 1.5, 1.5], gap="small")
        is_disabled = st.session_state.selected_book_id is None
        
        with c_qty:
            qty = st.number_input("qty", min_value=1, value=1, label_visibility="collapsed")
            
        with c_in:
            st.markdown('<div class="footer-btn btn-in">', unsafe_allow_html=True)
            if st.button("入庫", key="footer_in", disabled=is_disabled, use_container_width=True):
                update_stock(ws_items, ws_logs, st.session_state.selected_book_id, st.session_state.selected_book_name, st.session_state.selected_book_stock, qty, "入庫")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with c_out:
            st.markdown('<div class="footer-btn btn-out">', unsafe_allow_html=True)
            if st.button("出庫", key="footer_out", disabled=is_disabled, use_container_width=True):
                update_stock(ws_items, ws_logs, st.session_state.selected_book_id, st.session_state.selected_book_name, st.session_state.selected_book_stock, qty, "出庫")
            st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 新規登録タブ
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
                    st.error("必須")
                else:
                    nid = int(df_items['商品ID'].max()) + 1 if not df_items.empty else 1
                    ws_items.append_row([int(nid), str(fname), str(isbn), str(fpub), int(stock), int(alert), str(loc)])
                    add_log(ws_logs, "新規登録", nid, fname, stock)
                    st.success(f"登録完了: {fname}")
                    st.rerun()

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
        
        st.session_state.selected_book_stock = new_stock
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
