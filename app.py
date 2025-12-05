import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定・デザイン調整（スマホ完全対応・最終版）
# ---------------------------------------------------------

st.set_page_config(page_title="教科書在庫管理", layout="centered", initial_sidebar_state="collapsed")

# カスタムCSS：スマホの狭い画面に特化したスタイル
st.markdown("""
<style>
    /* 全体のリセットと文字サイズ縮小 */
    body { 
        font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif; 
        color: #333; 
        margin: 0; padding: 0;
        font-size: 11px !important; /* ベース文字サイズを小さく */
    }
    
    /* 左右の余白を極限まで減らす */
    .block-container { 
        padding-top: 1rem; 
        padding-bottom: 2rem; 
        padding-left: 0.2rem !important; 
        padding-right: 0.2rem !important; 
        max-width: 100% !important;
    }
    
    /* ヘッダータイトル（見切れ防止） */
    h3 {
        font-size: 1.2rem !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    /* 検索バー周り */
    div[data-testid="stTextInput"] { margin-bottom: 5px; }
    div[data-testid="stTextInput"] input { font-size: 12px; height: 30px; }
    
    /* --------------------------------------------------- */
    /* テーブルレイアウト（強制横並び・スクロールなし） */
    /* --------------------------------------------------- */
    
    /* Streamlitのカラムを強制的に横並び＆余白ゼロにする */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 2px !important;
    }
    
    div[data-testid="column"] {
        min-width: 0px !important;
        padding: 0 !important;
        overflow: hidden !important;
        flex: 1 1 auto !important; /* 柔軟に伸縮 */
    }

    /* ヘッダー行（黒背景） */
    .table-header {
        background-color: #222;
        color: white;
        padding: 6px 2px;
        font-weight: bold;
        font-size: 10px; /* 小さく */
        text-align: center;
        border-radius: 3px 3px 0 0;
        display: flex;
        align-items: center;
        margin-top: 5px;
    }

    /* データ行（コンテナ） */
    .row-container {
        border-bottom: 1px solid #eee;
        padding: 4px 0;
        display: flex;
        align-items: center;
        height: 50px; /* 行の高さを固定して整える */
    }

    /* --------------------------------------------------- */
    /* 各要素のデザイン */
    /* --------------------------------------------------- */

    /* 教科書名 */
    .book-name {
        font-weight: bold;
        font-size: 11px;
        line-height: 1.1;
        white-space: normal; /* 折り返し許可 */
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2; /* 2行まで表示 */
        -webkit-box-orient: vertical;
    }
    
    /* 在庫数（2桁入るギリギリ） */
    .stock-num {
        font-size: 13px;
        font-weight: bold;
        text-align: center;
    }
    
    /* 数量入力欄 */
    div[data-testid="stNumberInput"] input {
        padding: 0 !important;
        text-align: center !important;
        height: 25px !important;
        font-size: 12px !important;
        width: 100% !important;
    }
    div[data-testid="stNumberInput"] { margin: 0 !important; }

    /* 操作ボタン（枠線スタイル） */
    /* 入庫ボタン（薄緑文字・薄緑枠） */
    button[kind="secondary"] {
        background-color: transparent !important;
        color: #28a745 !important;
        border: 1px solid #28a745 !important;
        padding: 0 !important;
        height: 22px !important;
        font-size: 10px !important;
        line-height: 20px !important;
        border-radius: 3px !important;
        margin-bottom: 2px !important; /* 上下配置用 */
    }
    
    /* 出庫ボタン（朱色文字・朱色枠） */
    button[kind="primary"] {
        background-color: transparent !important;
        color: #e74c3c !important;
        border: 1px solid #e74c3c !important;
        padding: 0 !important;
        height: 22px !important;
        font-size: 10px !important;
        line-height: 20px !important;
        border-radius: 3px !important;
    }
    
    /* 更新ボタンのみ例外（グレー背景） */
    div.stHorizontalBlock > div:nth-child(2) button {
        background-color: #f0f0f0 !important;
        color: #333 !important;
        border: 1px solid #ccc !important;
        height: 30px !important;
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
    c_search, c_update = st.columns([3.5, 1])
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

    tab_list, tab_add = st.tabs(["📦 在庫リスト", "➕ 新規登録"])

    # ---------------------------------------------------------
    # 在庫リスト（最終調整版）
    # ---------------------------------------------------------
    with tab_list:
        # ヘッダー（比率調整）
        # 名前: 45%, 在庫: 15%, 数量: 15%, 操作: 25%
        # st.columns の比率: [4.5, 1.5, 1.5, 2.5]
        
        st.markdown("""
        <div class="table-header">
            <div style="flex:4.5; text-align:left; padding-left:2px;">教科書名</div>
            <div style="flex:1.5;">在庫</div>
            <div style="flex:1.5;">数量</div>
            <div style="flex:2.5;">操作</div>
        </div>
        """, unsafe_allow_html=True)

        if df_display.empty:
            st.info("データなし")
        
        for index, row in df_display.iterrows():
            item_id = int(row['商品ID'])
            name = row['教科書名']
            stock = int(row['現在在庫数'])
            alert = int(row['発注点'])
            
            is_low = stock <= alert
            stock_color = "#d63031" if is_low else "#333"
            bg_style = "background-color: #fff5f5;" if is_low else "background-color: #fff;"

            # 行のコンテナ
            st.markdown(f'<div class="row-container" style="{bg_style}">', unsafe_allow_html=True)
            
            # カラム比率（ヘッダーと一致させる）
            c1, c2, c3, c4 = st.columns([4.5, 1.5, 1.5, 2.5], gap="small")
            
            with c1:
                # 教科書名（2行まで表示）
                st.markdown(f'<div class="book-name">{name}</div>', unsafe_allow_html=True)
                
            with c2:
                # 在庫数
                st.markdown(f'<div class="stock-num" style="color:{stock_color};">{stock}</div>', unsafe_allow_html=True)
                
            with c3:
                # 数量入力（初期値1）
                qty = st.number_input("qty", min_value=1, value=1, label_visibility="collapsed", key=f"q_{item_id}")
                
            with c4:
                # 操作ボタン（入庫・出庫を配置）
                # 横並びにすると幅が足りないので、CSSで調整されたボタンを配置
                # Streamlitのcolumnの中にさらにcolumnを作ると崩れるので、シンプルに2つ並べる
                # ここではボタンのCSS（margin-bottom）で上下に並ぶようにするか、横に並ぶかは幅次第
                
                c_in, c_out = st.columns(2, gap="small")
                with c_in:
                    if st.button("入庫", key=f"in_{item_id}"):
                        update_stock(ws_items, ws_logs, item_id, name, stock, qty, "入庫")
                with c_out:
                    if st.button("出庫", key=f"out_{item_id}", type="primary"):
                        update_stock(ws_items, ws_logs, item_id, name, stock, qty, "出庫")

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
        row = [log_id, now, action_type, int(item_id), int(change_val), str(item_name)]
        ws_logs.append_row(row)
    except:
        pass 

if __name__ == "__main__":
    main()
