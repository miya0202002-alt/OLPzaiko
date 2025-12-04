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

# カスタムCSS：スマホでの表示崩れを物理的に防ぐ設定
st.markdown("""
<style>
    /* 1. スマホでもカラムを絶対に縦積みにしない（強制横並び） */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
    }
    
    /* 2. カラムの余白を極限まで削ってスペース確保 */
    div[data-testid="column"] {
        min-width: 10px !important; /* 縮小限界を小さく */
        padding: 0 1px !important;  /* 隣との隙間を最小に */
        overflow: hidden !important; /* はみ出し防止 */
    }

    /* 3. 全体の文字サイズをスマホ用に調整 */
    .small-font { font-size: 12px !important; }
    p, span, div { font-size: 13px; }
    
    /* 4. ボタンのデザイン（小さく押しやすく） */
    div.stButton > button {
        padding: 0px !important;
        min-height: 38px !important;
        height: 38px !important;
        font-size: 12px !important;
        font-weight: bold !important;
        border-radius: 4px !important;
        width: 100%;
        margin: 0 !important;
    }
    
    /* 入庫ボタン（緑） */
    button[kind="secondary"] {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
    }
    /* 出庫ボタン（朱色） */
    button[kind="primary"] {
        background-color: #e74c3c !important;
        color: white !important;
        border: none !important;
    }
    /* 更新ボタン（グレー） */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button {
        background-color: #f0f0f0 !important;
        color: #333 !important;
        border: 1px solid #ccc !important;
    }

    /* 5. 数量入力欄の調整 */
    div[data-testid="stNumberInput"] input {
        padding: 0px !important;
        text-align: center !important;
        min-height: 38px !important;
        height: 38px !important;
        font-size: 14px !important;
    }
    /* ラベル分の余白を消す */
    div[data-testid="stNumberInput"] > label { display: none; }
    div[data-testid="stNumberInput"] { margin-top: -15px !important; margin-bottom: 0px !important; }

    /* 6. 行ごとの区切り線 */
    .row-separator {
        border-bottom: 1px solid #e0e0e0;
        margin-top: 5px;
        margin-bottom: 5px;
    }
    
    /* ヘッダーのスタイル */
    .header-text {
        font-weight: bold;
        font-size: 11px;
        text-align: center;
        background-color: #333;
        color: white;
        padding: 8px 0;
        border-radius: 4px;
        margin-bottom: 5px;
    }
    
    /* 「変な□」を消す */
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    
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
        # ログ読み込みエラー回避
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
    # 比率 [3, 1] で横並び
    c_search, c_update = st.columns([3, 1])
    with c_search:
        search_query = st.text_input("search", placeholder="教科書名...", label_visibility="collapsed")
    with c_update:
        # ご指示通りの表記「↻ 更新」
        if st.button("↻ 更新"): st.rerun()

    # 並べ替え（名前順削除）
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

    tab_list, tab_add = st.tabs(["📦 在庫リスト", "➕ 新規登録"])

    # ---------------------------------------------------------
    # 在庫リスト（ズレなし・完全横並び）
    # ---------------------------------------------------------
    with tab_list:
        # カラム比率定義（ここを統一することでズレを防ぐ）
        # [名前4, 在庫1, 数量1.5, 入1, 出1] -> 合計8.5
        # スマホ幅に合わせて調整
        col_ratio = [3.5, 1, 1.3, 1, 1]

        # ヘッダー行（データ行と同じst.columnsで作る）
        h1, h2, h3, h4, h5 = st.columns(col_ratio)
        h1.markdown('<div class="header-text" style="text-align:left; padding-left:5px;">教科書名</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header-text">在庫</div>', unsafe_allow_html=True)
        h3.markdown('<div class="header-text">数</div>', unsafe_allow_html=True)
        h4.markdown('<div class="header-text">入</div>', unsafe_allow_html=True)
        h5.markdown('<div class="header-text">出</div>', unsafe_allow_html=True)

        if df_display.empty:
            st.info("データなし")
        
        for index, row in df_display.iterrows():
            item_id = int(row['商品ID'])
            name = row['教科書名']
            stock = int(row['現在在庫数'])
            alert = int(row['発注点'])
            
            is_low = stock <= alert
            stock_color = "#d63031" if is_low else "#333"
            
            # データ行（ヘッダーと全く同じ比率）
            c1, c2, c3, c4, c5 = st.columns(col_ratio)
            
            with c1:
                # 教科書名（太字）
                st.markdown(f'<div style="font-weight:bold; line-height:1.2; padding-top:8px;">{name}</div>', unsafe_allow_html=True)
                
            with c2:
                # 在庫数
                st.markdown(f'<div style="text-align:center; font-weight:bold; color:{stock_color}; padding-top:8px;">{stock}</div>', unsafe_allow_html=True)
                
            with c3:
                # 数量入力（初期値1、ラベルなし）
                # keyを変数にすることで確実にレンダリング
                qty = st.number_input("qty", min_value=1, value=1, label_visibility="collapsed", key=f"q_{item_id}")
                
            with c4:
                # 入庫ボタン（緑）
                if st.button("入", key=f"in_{item_id}"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "入庫")
            
            with c5:
                # 出庫ボタン（赤）
                if st.button("出", key=f"out_{item_id}", type="primary"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "出庫")

            # 行の下に区切り線を入れる（視認性向上）
            st.markdown('<div class="row-separator"></div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 新規登録
    # ---------------------------------------------------------
    with tab_add:
        st.markdown("##### 新規登録")
        with st.form("add"):
            # 候補 + 手入力
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
            # 初期値 1
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
# ログ記録機能（確実版）
# ---------------------------------------------------------
def update_stock(ws_items, ws_logs, item_id, item_name, current_stock, quantity, action_type):
    new_stock = current_stock + quantity if action_type == "入庫" else current_stock - quantity
    if new_stock < 0:
        st.error("在庫不足")
        return
    try:
        cell = ws_items.find(str(item_id), in_column=1)
        ws_items.update_cell(cell.row, 5, new_stock)
        
        # 符号付きで記録
        change = quantity if action_type == "入庫" else -quantity
        add_log(ws_logs, action_type, item_id, item_name, change)
        
        st.toast(f"{action_type}完了 (残{new_stock})")
        st.rerun()
    except Exception as e:
        st.error(f"エラー: {e}")

def add_log(ws_logs, action_type, item_id, item_name, change_val):
    try:
        # append_row で一番下に追加（これが一番確実）
        # ログIDはタイムスタンプで簡易生成（競合回避のため）
        log_id = int(datetime.now().timestamp())
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        
        row = [log_id, now, action_type, int(item_id), int(change_val), str(item_name)]
        ws_logs.append_row(row)
    except:
        pass # ログエラーで止まらないようにする

if __name__ == "__main__":
    main()
