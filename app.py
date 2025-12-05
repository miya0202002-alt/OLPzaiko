import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定
# ---------------------------------------------------------
# 1. ページ設定は "centered" に戻します
st.set_page_config(page_title="教科書在庫管理", layout="centered", initial_sidebar_state="expanded")

# ---------------------------------------------------------
# CSS (スマホ対応：PCは横並び、スマホは縦積み)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* 全体フォント */
    body { font-family: -apple-system, sans-serif; color: #333; margin: 0; padding: 0; }
    
    /* アプリ全体の横幅調整（スマホでの横揺れ防止） */
    .block-container { 
        padding-top: 3rem !important; 
        padding-bottom: 120px !important; /* フッター用余白 */
        padding-left: 1rem !important; 
        padding-right: 1rem !important; 
        max-width: 100% !important;
    }

    /* PC画面（幅640px以上）の時は、画面の中央に寄せる */
    @media (min-width: 640px) {
        .block-container {
            max-width: 700px !important;
            margin: 0 auto !important;
        }
        /* フッターもPCでは幅を合わせる */
        section[data-testid="stSidebar"] {
            width: 700px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
        }
    }

    /* ========== スマホ画面（幅640px以下）の時の強制ルール ========== */
    @media (max-width: 640px) {
        
        /* 1. カラム（列）の強制縦積み */
        /* 横並びの設定を解除し、全ての列を縦1列（幅100%）にします */
        div[data-testid="column"] {
            width: 100% !important;
            flex: 1 1 auto !important;
            min-width: 100% !important;
            margin-bottom: 8px !important; /* 縦並びの要素間に隙間を作る */
        }

        /* 2. ヘッダーや行のコンテナが広がらないようにする */
        div[data-testid="stVerticalBlock"] {
            max-width: 100% !important;
            overflow-x: hidden !important; /* 横スクロールを禁止 */
        }

        /* 3. ボタンや入力欄のサイズ調整 */
        .stButton button, div[data-testid="stNumberInput"] input {
            width: 100% !important;
            min-width: 0px !important; /* 最小幅制限を解除 */
        }
        
        /* スマホではリストのヘッダー（項目名）を隠す（縦積みだとズレて見えるため） */
        .table-header {
            display: none !important;
        }
        
        /* 行の区切りを強調 */
        hr {
            margin-top: 1rem !important;
            margin-bottom: 1rem !important;
            border-top: 2px solid #eee !important;
        }
    }
    /* ========== ここまで ========== */


    /* タイトル */
    h3 { font-size: 1.4rem !important; margin-bottom: 0.5rem; font-weight: bold; }

    /* 下部固定パネル（フッター） */
    section[data-testid="stSidebar"] {
        position: fixed !important;
        bottom: 0 !important;
        top: auto !important;
        left: 0 !important;
        height: auto !important;
        background-color: #fff !important;
        border-top: 1px solid #ccc !important;
        box-shadow: 0 -2px 8px rgba(0,0,0,0.1) !important;
        z-index: 999999 !important;
        padding: 0px !important;
    }
    
    /* サイドバー内部調整 */
    section[data-testid="stSidebar"] .block-container {
        padding: 10px !important;
        margin: 0 !important;
        overflow: hidden !important;
    }
    
    /* 不要なパーツ削除 */
    div[data-testid="stSidebarNav"], button[kind="header"], [data-testid="stSidebarCollapsedControl"] { 
        display: none !important; 
    }

    /* ヘッダーボックス（PC用） */
    .header-box {
        background-color: #222;
        color: white;
        font-weight: bold;
        font-size: 11px;
        text-align: center;
        padding: 8px 2px;
        border-radius: 4px;
        width: 100%;
        display: block;
    }

    /* 教科書選択ボタン */
    div.row-btn button {
        background-color: white !important;
        color: #333 !important;
        border: 1px solid #eee !important;
        text-align: left !important;
        font-weight: bold !important;
        font-size: 14px !important; /* 少し大きく */
        padding: 8px 10px !important;
        white-space: normal !important;
        line-height: 1.3 !important;
        width: 100% !important;
    }
    div.row-btn button:focus {
        border-color: #28a745 !important;
        background-color: #f0fff0 !important;
    }

    /* ボタン・入力欄の色設定 */
    .footer-btn button { height: 40px !important; font-weight: bold !important; }
    div[data-testid="stNumberInput"] input { height: 40px !important; text-align: center !important; }
    
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

    st.markdown("### 教科書在庫管理")
    
    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None: return

    df_items.columns = df_items.columns.str.strip()
    cols_to_num = ['商品ID', '現在在庫数', '発注点']
    for col in cols_to_num:
        if col in df_items.columns:
            df_items[col] = pd.to_numeric(df_items[col], errors='coerce').fillna(0).astype(int)

    # ---------------------------------------------------------
    # メニュー切り替え（ラジオボタン）
    # ---------------------------------------------------------
    menu = st.radio("メニュー", ["在庫リスト", "⊕教科書を追加"], horizontal=True, label_visibility="collapsed")

    # =========================================================
    # 「在庫リスト」モード
    # =========================================================
    if menu == "在庫リスト":
        
        # 検索・更新
        c_search, c_update = st.columns([3.5, 1])
        with c_search:
            search_query = st.text_input("search", placeholder="検索...", label_visibility="collapsed")
        with c_update:
            if st.button("↻ 更新", use_container_width=True): 
                st.session_state.selected_book_id = None
                st.rerun()

        if search_query:
            mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
            df_display = df_items[mask]
        else:
            df_display = df_items

        # --- ヘッダー行（スマホではCSSで非表示になります） ---
        h_cols = st.columns([3.5, 1.5])
        h_cols[0].markdown('<div class="header-box" style="text-align:left; padding-left:10px;">教科書名 (タップして選択)</div>', unsafe_allow_html=True)
        h_cols[1].markdown('<div class="header-box">在庫</div>', unsafe_allow_html=True)

        # --- データ一覧 ---
        for index, row in df_display.iterrows():
            item_id = int(row['商品ID'])
            name = row['教科書名']
            stock = int(row['現在在庫数'])
            alert = int(row['発注点'])
            
            is_low = stock <= alert
            stock_color = "#e74c3c" if is_low else "#333"
            stock_weight = "bold" if is_low else "bold"

            # 行の表示
            # PCでは横並び、スマホではCSSにより自動で縦積み（カード化）されます
            cols = st.columns([3.5, 1.5])
            
            with cols[0]:
                # 教科書名ボタン
                st.markdown('<div class="row-btn">', unsafe_allow_html=True)
                label = f"{name}"
                if st.button(label, key=f"sel_{item_id}", use_container_width=True):
                    st.session_state.selected_book_id = item_id
                    st.session_state.selected_book_name = name
                    st.session_state.selected_book_stock = stock
                st.markdown('</div>', unsafe_allow_html=True)
            
            with cols[1]:
                # 在庫数
                st.markdown(f"""
                <div style="text-align:center; height:100%; display:flex; align-items:center; justify-content:center; padding: 5px;">
                    <span style="font-size:16px; font-weight:{stock_weight}; color:{stock_color};">在庫: {stock}</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<hr style='margin:0; border-top:1px solid #eee;'>", unsafe_allow_html=True)

        # --- フッター操作パネル（在庫リスト時のみ表示） ---
        with st.sidebar:
            display_name = st.session_state.selected_book_name
            display_stock = f"(在庫: {st.session_state.selected_book_stock})" if st.session_state.selected_book_id else ""
            st.markdown(f"<div style='font-size:12px; color:#555; margin-bottom:5px; white-space:nowrap; overflow:hidden;'>選択中: <b>{display_name}</b> {display_stock}</div>", unsafe_allow_html=True)
            
            # 操作ボタン（PCは横並び、スマホはCSSで縦積みになるのを防ぐため、ここだけは横並び維持のCSSが効くようにする）
            # ただしフッター内はスペースが狭いので、st.columns で配置
            c_qty, c_in, c_out = st.columns([1, 1.5, 1.5], gap="small")
            
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

    # =========================================================
    # 「⊕教科書を追加」モード
    # =========================================================
    elif menu == "⊕教科書を追加":
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
