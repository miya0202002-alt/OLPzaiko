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
# CSS (スマホレイアウト強制・パネル固定・必須マーク)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* 1. 全体設定 */
    body { font-family: -apple-system, sans-serif; color: #333; margin: 0; padding: 0; }
    
    .block-container { 
        padding-top: 4.5rem !important; 
        padding-bottom: 120px !important; /* パネル用に余白確保 */
        padding-left: 0.5rem !important; 
        padding-right: 0.5rem !important; 
    }

    /* PC画面用制限 */
    @media (min-width: 640px) {
        .block-container { max-width: 50vw !important; margin: 0 auto !important; }
        section[data-testid="stSidebar"] { width: 50vw !important; left: 50% !important; transform: translateX(-50%) !important; }
    }

    /* 2. タイトル */
    h3 { font-size: 1.5rem !important; margin-bottom: 1rem; font-weight: bold; line-height: 1.4; }

    /* 3. 下部固定パネル（絶対に常時表示・折りたたみ不可・横一列） */
    section[data-testid="stSidebar"] {
        position: fixed !important;
        bottom: 0 !important;
        top: auto !important;
        left: 0 !important;
        height: auto !important;
        width: 100% !important;
        min-width: 100% !important;
        background-color: #fff !important;
        border-top: 1px solid #ccc !important;
        box-shadow: 0 -2px 5px rgba(0,0,0,0.1) !important;
        z-index: 999999 !important;
        padding: 5px 5px !important;
        transform: none !important; /* 強制的に表示位置を固定 */
        display: block !important;
        visibility: visible !important;
    }
    
    /* 折りたたみボタン等のパーツを完全消去 */
    div[data-testid="stSidebarNav"], 
    button[kind="header"],
    div[data-testid="collapsedControl"], 
    [data-testid="stSidebarCollapsedControl"] {
        display: none !important; 
    }
    
    section[data-testid="stSidebar"] .block-container { 
        padding: 0 !important; 
        max-width: 100% !important; 
        width: 100% !important;
    }

    /* ★重要：スマホでもカラムを「横並び」に強制する設定 */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 2px !important;
        align-items: center !important;
    }
    div[data-testid="column"] {
        flex: 1 1 auto !important;
        width: auto !important;
        min-width: 0px !important; /* これがないとスマホで縦になる */
        padding: 0 1px !important;
        overflow: visible !important;
    }

    /* 4. ヘッダーとリストのデザイン */
    .header-box {
        background-color: #222;
        color: white;
        font-weight: bold;
        font-size: 11px;
        text-align: center;
        padding: 8px 2px;
        border-radius: 4px;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        white-space: nowrap; /* 折り返し禁止 */
    }

    div.row-btn button {
        background-color: white !important;
        color: #333 !important;
        border: 1px solid #eee !important;
        text-align: left !important;
        font-weight: bold !important;
        font-size: 13px !important;
        min-height: 45px !important;
        padding: 5px 10px !important;
        white-space: normal !important;
        line-height: 1.2 !important;
        width: 100%;
    }
    div.row-btn button:focus {
        border-color: #28a745 !important;
        background-color: #f0fff0 !important;
    }

    /* 5. パネル内のボタン・入力欄 */
    .footer-btn button {
        height: 38px !important;
        font-size: 12px !important;
        font-weight: bold !important;
        border-radius: 4px !important;
        padding: 0 !important;
        line-height: 1 !important;
        margin: 0 !important;
    }
    
    div[data-testid="stNumberInput"] input {
        height: 38px !important;
        text-align: center !important;
        font-size: 14px !important;
        padding: 0 !important;
    }
    div[data-testid="stNumberInput"] { margin: 0 !important; width: 100% !important; }

    /* 色設定 */
    .btn-in button { background-color: #28a745 !important; color: white !important; border: none; }
    .btn-out button { background-color: #e74c3c !important; color: white !important; border: none; }
    
    button:disabled {
        background-color: #e0e0e0 !important;
        color: #999 !important;
        border: 1px solid #ccc !important;
    }

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

    st.markdown("### 教科書在庫管理表")
    
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

        # ヘッダー行（スマホでも絶対に横並びになる比率とCSS）
        # 比率: [教科書名(4), 在庫(1.5)] -> 1行に収める
        h1, h2 = st.columns([4, 1.5])
        with h1:
            st.markdown('<div class="header-box" style="justify-content:flex-start; padding-left:10px;">教科書名（タップして選択）</div>', unsafe_allow_html=True)
        with h2:
            st.markdown('<div class="header-box">在庫</div>', unsafe_allow_html=True)

        for index, row in df_display.iterrows():
            item_id = int(row['商品ID'])
            name = row['教科書名']
            stock = int(row['現在在庫数'])
            alert = int(row['発注点'])
            
            is_low = stock <= alert
            stock_color = "#e74c3c" if is_low else "#333"
            stock_weight = "bold" if is_low else "bold"

            # データ行（横並び強制）
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
                    <span style="font-size:16px; font-weight:{stock_weight}; color:{stock_color};">{stock}</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<hr style='margin:0; border-top:1px solid #eee;'>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 下部固定操作パネル（絶対に常時表示・横1列）
    # ---------------------------------------------------------
    with st.sidebar:
        # 情報表示
        display_name = st.session_state.selected_book_name
        if st.session_state.selected_book_id is None:
            display_name = "（リストから選択）"
            
        st.markdown(f"<div style='font-size:11px; color:#666; margin-bottom:2px; white-space:nowrap; overflow:hidden;'>選択: <b>{display_name}</b> (在庫: {st.session_state.selected_book_stock})</div>", unsafe_allow_html=True)
        
        # 操作エリア：横一列に強制配置
        # 比率: [数(1.2), 入(1.5), 出(1.5)]
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
    # 新規登録タブ（必須マーク追加）
    # ---------------------------------------------------------
    with tab_add:
        st.markdown("##### 新規登録")
        with st.form("add"):
            names = list(df_items['教科書名'].unique()) if '教科書名' in df_items.columns else []
            name_sel = st.selectbox("教科書名 :red[*]", options=names + ["新規入力"], index=None, placeholder="選択...")
            name_in = ""
            if name_sel == "新規入力": name_in = st.text_input("入力")
            
            pubs = list(df_items['出版社'].unique()) if '出版社' in df_items.columns else []
            pub_sel = st.selectbox("出版社 :red[*]", options=pubs + ["その他"], index=None, placeholder="選択...")
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
                    st.error("必須項目が未入力です")
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
