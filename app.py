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
    /* 全体のフォントと色 */
    body { font-family: "Helvetica Neue", Arial, sans-serif; color: #333; background-color: #ffffff; }
    
    /* アプリ全体の枠線（メリハリ） */
    .main-container {
        border: 2px solid #333;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
        background-color: white;
    }

    /* 検索バー周りの枠線 */
    .search-box-container {
        border: 2px solid #0056b3; /* 青っぽい枠で強調 */
        border-radius: 8px;
        padding: 15px;
        background-color: #f0f7ff;
        margin-bottom: 20px;
    }

    /* テーブルヘッダー（GAS風 黒背景） */
    .table-header {
        background-color: #222;
        color: #fff;
        padding: 10px 5px;
        font-weight: bold;
        font-size: 0.9em;
        border-radius: 5px 5px 0 0;
        margin-bottom: 0;
    }

    /* 1行レイアウトのスタイル */
    .row-container {
        border-bottom: 1px solid #ccc;
        border-left: 1px solid #ccc;
        border-right: 1px solid #ccc;
        padding: 10px 5px;
        background-color: #fff;
        display: flex;
        align-items: center;
    }
    .row-container:last-child {
        border-radius: 0 0 5px 5px;
    }

    /* 文字のメリハリ */
    .text-title { font-size: 1.1em; font-weight: bold; color: #000; display: block; }
    .text-sub { font-size: 0.8em; color: #666; }
    .text-stock { font-size: 1.2em; font-weight: bold; }
    .text-alert { color: #d63031; font-weight: bold; } /* 不足時の赤 */

    /* ボタンのデザイン調整 */
    /* 入庫ボタン（緑背景・白文字）を再現するために、特定のクラスを持つボタンを強制上書き */
    div[data-testid="column"] button {
        width: 100%;
        border-radius: 4px;
        font-weight: bold;
        border: none;
        height: 2.5em;
    }
    
    /* StreamlitのPrimaryボタン（出庫）を朱色に */
    button[kind="primary"] {
        background-color: #e74c3c !important;
        color: white !important;
    }
    
    /* Secondaryボタン（入庫）を緑色に強制変更 */
    /* 注: 更新ボタンなど他のボタンにも影響しないよう、列の中のボタンであることを意識 */
    button[kind="secondary"] {
        background-color: #28a745 !important;
        color: white !important;
        border: 1px solid #28a745 !important;
    }
    /* 更新ボタンだけはグレーに戻す */
    div.stHorizontalBlock button[kind="secondary"] {
        background-color: #f0f0f0 !important;
        color: #333 !important;
        border: 1px solid #ccc !important;
    }
    
    /* 入力欄の微調整 */
    input { font-size: 16px !important; }
    
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
        df_logs = pd.DataFrame(logs_data[1:], columns=logs_data[0]) if logs_data else pd.DataFrame()
        
        return sh, ws_items, df_items, ws_logs, df_logs
    except Exception as e:
        st.error(f"接続エラー: {e}")
        return None, None, None, None, None

def main():
    # アプリ全体を囲む枠（デザイン的メリハリ）
    with st.container():
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        
        st.markdown("### 教科書在庫管理")
        
        sh, ws_items, df_items, ws_logs, df_logs = load_data()
        if sh is None: 
            st.markdown('</div>', unsafe_allow_html=True)
            return

        # データ前処理
        df_items.columns = df_items.columns.str.strip()
        cols_to_num = ['商品ID', '現在在庫数', '発注点']
        for col in cols_to_num:
            if col in df_items.columns:
                df_items[col] = pd.to_numeric(df_items[col], errors='coerce').fillna(0).astype(int)

        # ---------------------------------------------------------
        # 検索・更新・並べ替えエリア（枠で囲む）
        # ---------------------------------------------------------
        st.markdown('<div class="search-box-container">', unsafe_allow_html=True)
        
        c_search, c_update = st.columns([3, 1])
        with c_search:
            search_query = st.text_input("検索", placeholder="教科書名、出版社など...", label_visibility="collapsed")
        with c_update:
            if st.button("↻ 更新"): st.rerun()
            
        # 並べ替え機能
        sort_mode = st.radio("並べ替え:", ["追加日 (新しい順)", "在庫数 (少ない順)", "名前 (あいうえお順)"], horizontal=True)
        if sort_mode == "追加日 (新しい順)":
            if '商品ID' in df_items.columns:
                df_items = df_items.sort_values('商品ID', ascending=False)
        elif sort_mode == "在庫数 (少ない順)":
             df_items = df_items.sort_values('現在在庫数', ascending=True)
        elif sort_mode == "名前 (あいうえお順)":
             df_items = df_items.sort_values('教科書名', ascending=True)
             
        st.markdown('</div>', unsafe_allow_html=True)

        # フィルタリング
        if search_query:
            mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
            df_display = df_items[mask]
        else:
            df_display = df_items

        # タブ切り替え（履歴タブは削除）
        tab_list, tab_add = st.tabs(["📦 在庫リスト", "➕ 新規登録"])

        # ---------------------------------------------------------
        # 在庫リストタブ（GAS風 1行レイアウト）
        # ---------------------------------------------------------
        with tab_list:
            # ヘッダー行（黒背景）
            st.markdown("""
            <div class="table-header">
                <div style="display:flex;">
                    <div style="flex:3; padding-left:10px;">教科書情報</div>
                    <div style="flex:1; text-align:center;">在庫</div>
                    <div style="flex:1; text-align:center;">数量</div>
                    <div style="flex:1; text-align:center;">入庫</div>
                    <div style="flex:1; text-align:center;">出庫</div>
                </div>
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
                loc = row['保管場所']
                isbn = row.get('ISBNコード', '-')
                
                is_low = stock <= alert
                stock_class = "text-alert" if is_low else ""
                bg_style = "background-color: #fff0f0;" if is_low else "" # 不足時は背景を薄い赤に

                # 1行のコンテナ開始
                st.markdown(f'<div class="row-container" style="{bg_style}">', unsafe_allow_html=True)
                
                # StreamlitのColumnsを使って1行に配置
                # 比率: 情報(3) : 在庫(1) : 入力(1) : 入庫(1) : 出庫(1)
                c_info, c_stock, c_qty, c_in, c_out = st.columns([3, 1, 1, 1, 1])
                
                with c_info:
                    # メリハリのある文字情報
                    st.markdown(f"""
                    <span class="text-title">{name}</span>
                    <span class="text-sub">{pub} | {loc} <br> ISBN: {isbn}</span>
                    """, unsafe_allow_html=True)
                    
                with c_stock:
                    st.markdown(f'<div style="text-align:center;"><span class="text-stock {stock_class}">{stock}</span></div>', unsafe_allow_html=True)
                    
                with c_qty:
                    # 数量入力（初期値1）
                    qty = st.number_input("数量", min_value=1, value=1, label_visibility="collapsed", key=f"q_{item_id}")
                    
                with c_in:
                    # 入庫ボタン（CSSで緑になります）
                    if st.button("入庫", key=f"in_{item_id}"):
                        update_stock(ws_items, ws_logs, item_id, name, stock, qty, "入庫")
                        
                with c_out:
                    # 出庫ボタン（Primary＝朱色）
                    if st.button("出庫", key=f"out_{item_id}", type="primary"):
                        update_stock(ws_items, ws_logs, item_id, name, stock, qty, "出庫")

                # 1行のコンテナ終了
                st.markdown('</div>', unsafe_allow_html=True)

        # ---------------------------------------------------------
        # 新規登録タブ
        # ---------------------------------------------------------
        with tab_add:
            st.markdown("##### 新しい教科書の登録")
            with st.form("add"):
                # 教科書名：プルダウン + 手入力
                # GSSから候補を取得し、None（選択なし）を初期値にする
                existing_names = list(df_items['教科書名'].unique()) if '教科書名' in df_items.columns else []
                name_select = st.selectbox("教科書名", options=existing_names + ["新規入力"], index=None, placeholder="教科書名を選択してください...")
                
                name_input = ""
                if name_select == "新規入力":
                    name_input = st.text_input("新しい教科書名を入力")
                
                # 出版社：プルダウン + 手入力
                existing_pubs = list(df_items['出版社'].unique()) if '出版社' in df_items.columns else []
                pub_select = st.selectbox("出版社", options=existing_pubs + ["その他（手入力）"], index=None, placeholder="出版社を選択してください...")
                
                pub_input = ""
                if pub_select == "その他（手入力）":
                    pub_input = st.text_input("出版社名を入力")
                    
                c1, c2 = st.columns(2)
                isbn = c1.text_input("ISBN (任意)")
                loc = c2.text_input("保管場所 (任意)")
                
                c3, c4 = st.columns(2)
                # 初期値を1に変更
                stock = c3.number_input("初期在庫 *", min_value=0, value=1)
                alert = c4.number_input("発注点", min_value=0, value=1)
                
                if st.form_submit_button("登録", use_container_width=True):
                    # 入力値の決定
                    final_name = name_input if name_select == "新規入力" else name_select
                    final_pub = pub_input if pub_select == "その他（手入力）" else pub_select
                    
                    if not final_name:
                        st.error("教科書名を選択または入力してください")
                    elif not final_pub:
                        st.error("出版社を選択または入力してください")
                    else:
                        new_id = int(df_items['商品ID'].max()) + 1
                        # 型を厳密に変換してリスト作成
                        new_row = [int(new_id), str(final_name), str(isbn), str(final_pub), int(stock), int(alert), str(loc)]
                        ws_items.append_row(new_row)
                        add_log(ws_logs, "新規登録", new_id, final_name, stock)
                        st.success(f"「{final_name}」を登録しました")
                        st.rerun()

        st.markdown('</div>', unsafe_allow_html=True) # メイン枠の終了

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
        # GSSのデータ取得時に型チェックを強化
        latest = ws_logs.cell(2, 1).value
        new_log_id = int(latest) + 1 if latest and str(latest).isdigit() else 1
    except: 
        new_log_id = 1
    
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    
    # 全てのデータを厳密にPython標準のint/str型に変換
    # これで「JSON serializable」エラーを回避し、確実にGSSに書き込む
    row_data = [
        int(new_log_id),
        str(now),
        str(action_type),
        int(item_id),
        int(change_val),
        str(item_name)
    ]
    
    ws_logs.insert_row(row_data, index=2)

if __name__ == "__main__":
    main()
