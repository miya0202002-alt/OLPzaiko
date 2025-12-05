import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定
# ---------------------------------------------------------
st.set_page_config(page_title="教科書在庫管理", layout="centered", initial_sidebar_state="collapsed")

# ---------------------------------------------------------
# CSS (スマホ最適化・固定フッター・ズレ防止)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* 全体設定 */
    body { font-family: -apple-system, sans-serif; color: #333; margin: 0; padding: 0; }
    .block-container { 
        padding-top: 1rem; padding-bottom: 150px !important; /* 下に余白を作ってパネルと被らないように */
        padding-left: 0.5rem !important; padding-right: 0.5rem !important; 
        max-width: 100% !important;
    }

    /* ▼▼▼ 下部固定パネル（サイドバーを改造） ▼▼▼ */
    section[data-testid="stSidebar"] {
        position: fixed !important;
        bottom: 0 !important;
        top: auto !important;
        left: 0 !important;
        width: 100% !important;
        height: auto !important;
        min-width: 100% !important;
        background-color: #fff !important;
        border-top: 2px solid #28a745 !important; /* 選択状態がわかるように緑のライン */
        box-shadow: 0 -4px 10px rgba(0,0,0,0.1) !important;
        z-index: 99999 !important;
        padding: 10px !important;
    }
    /* サイドバーの余計なパーツを消す */
    div[data-testid="stSidebarNav"], button[kind="header"] { display: none !important; }
    section[data-testid="stSidebar"] .block-container { padding: 0 !important; padding-bottom: 0 !important; }

    /* ▲▲▲ ここまで ▲▲▲ */

    /* ヘッダーとリストのズレ防止（共通クラス） */
    .grid-row {
        display: flex;
        align-items: center;
        border-bottom: 1px solid #eee;
        padding: 5px 0;
    }
    
    /* ヘッダーのデザイン */
    .header-box {
        background-color: #222;
        color: white;
        font-weight: bold;
        font-size: 11px;
        text-align: center;
        padding: 8px 2px;
        border-radius: 4px;
    }

    /* 教科書選択ボタン（リスト内のボタン） */
    div.row-btn button {
        background-color: white !important;
        color: #333 !important;
        border: 1px solid #ddd !important;
        text-align: left !important;
        font-weight: bold !important;
        font-size: 13px !important;
        height: auto !important;
        padding: 10px !important;
        white-space: normal !important; /* 折り返し許可 */
        line-height: 1.2 !important;
    }
    div.row-btn button:focus {
        border-color: #28a745 !important;
        background-color: #e6f9e6 !important;
    }

    /* 下部パネル内のボタン */
    .footer-btn-in button {
        background-color: #28a745 !important; color: white !important; border: none; height: 45px;
    }
    .footer-btn-out button {
        background-color: #e74c3c !important; color: white !important; border: none; height: 45px;
    }
    
    /* 入力欄 */
    input { text-align: center; font-size: 16px !important; }

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
    # セッション状態の初期化（選択した教科書を記憶するため）
    if 'selected_book_id' not in st.session_state:
        st.session_state.selected_book_id = None
    if 'selected_book_name' not in st.session_state:
        st.session_state.selected_book_name = ""
    if 'selected_book_stock' not in st.session_state:
        st.session_state.selected_book_stock = 0

    st.markdown("### 教科書在庫管理")
    
    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None: return

    # データ前処理
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
            st.session_state.selected_book_id = None # 更新時に選択解除
            st.rerun()

    # タブ
    tab_list, tab_add = st.tabs(["在庫リスト", "⊕教科書を追加"])

    # ---------------------------------------------------------
    # 在庫リスト（タップ選択式）
    # ---------------------------------------------------------
    with tab_list:
        # フィルタリング
        if search_query:
            mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
            df_display = df_items[mask]
        else:
            df_display = df_items

        # ヘッダー行（columnsを使用し、データ行と完全に同じ比率にする）
        # 比率: [教科書名ボタン(3.5), 在庫数(1), 不足アラート(1)]
        h1, h2, h3 = st.columns([3.5, 1, 1])
        h1.markdown('<div class="header-box" style="text-align:left; padding-left:10px;">教科書名をタップして選択</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-box">在庫</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-box">状態</div>', unsafe_allow_html=True)

        for index, row in df_display.iterrows():
            item_id = int(row['商品ID'])
            name = row['教科書名']
            stock = int(row['現在在庫数'])
            alert = int(row['発注点'])
            
            is_low = stock <= alert
            alert_text = "⚠️不足" if is_low else "OK"
            alert_color = "red" if is_low else "green"

            # 行の表示（すべて st.columns で統一＝ズレない）
            c1, c2, c3 = st.columns([3.5, 1, 1])
            
            with c1:
                # ★ここがポイント：教科書名をボタンにする
                # 押すと session_state に情報が入り、画面下のパネルが更新される
                # div.row-btn クラスでCSS装飾（テキストっぽく見せる）
                st.markdown('<div class="row-btn">', unsafe_allow_html=True)
                if st.button(f"{name}", key=f"sel_{item_id}", use_container_width=True):
                    st.session_state.selected_book_id = item_id
                    st.session_state.selected_book_name = name
                    st.session_state.selected_book_stock = stock
                st.markdown('</div>', unsafe_allow_html=True)
            
            with c2:
                # 在庫数
                st.markdown(f'<div style="text-align:center; padding-top:15px; font-weight:bold; font-size:14px;">{stock}</div>', unsafe_allow_html=True)
            
            with c3:
                # 状態
                st.markdown(f'<div style="text-align:center; padding-top:15px; font-weight:bold; color:{alert_color}; font-size:12px;">{alert_text}</div>', unsafe_allow_html=True)

            st.markdown("<hr style='margin:0; border-top:1px solid #eee;'>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 下部固定操作パネル（サイドバーを利用）
    # ---------------------------------------------------------
    with st.sidebar:
        if st.session_state.selected_book_id is None:
            st.info("👆 上のリストから教科書をタップしてください")
        else:
            # 選択中の教科書名を表示
            st.markdown(f"**選択中:** {st.session_state.selected_book_name}")
            st.caption(f"現在の在庫: {st.session_state.selected_book_stock} 冊")
            
            # 操作エリア
            c_qty, c_in, c_out = st.columns([1.5, 1.5, 1.5], gap="small")
            
            with c_qty:
                # 数量（初期値1・矢印あり）
                qty = st.number_input("数", min_value=1, value=1, label_visibility="collapsed")
            
            with c_in:
                st.markdown('<div class="footer-btn-in">', unsafe_allow_html=True)
                if st.button("入庫", use_container_width=True):
                    update_stock(ws_items, ws_logs, st.session_state.selected_book_id, st.session_state.selected_book_name, st.session_state.selected_book_stock, qty, "入庫")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with c_out:
                st.markdown('<div class="footer-btn-out">', unsafe_allow_html=True)
                if st.button("出庫", use_container_width=True):
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
        
        # 成功時にセッション情報の在庫も更新してリロード
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
