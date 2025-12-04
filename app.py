import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定・デザイン調整
# ---------------------------------------------------------

# アイコンなし、シンプルな設定
st.set_page_config(page_title="在庫管理システム", layout="centered", initial_sidebar_state="collapsed")

# カスタムCSS：シックでモダンなUI、入出庫ボタンの色分け
st.markdown("""
<style>
    /* 全体のフォントをスッキリさせる */
    body { font-family: "Helvetica Neue", Arial, sans-serif; color: #333; }
    
    /* ボタンのスタイル調整 */
    div.stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: bold;
        height: 2.8em;
        border: 1px solid #ddd;
    }
    
    /* 更新ボタン */
    div[data-testid="stHorizontalBlock"] button {
        background-color: #f8f9fa;
        color: #333;
    }

    /* カードデザイン */
    .item-container {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .item-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .item-title {
        font-size: 1.1em;
        font-weight: bold;
        color: #2c3e50;
    }
    .item-meta {
        font-size: 0.8em;
        color: #7f8c8d;
    }
    .stock-count {
        font-size: 1.4em;
        font-weight: bold;
    }
    .stock-unit { font-size: 0.6em; color: #7f8c8d; }
    
    /* 在庫不足時の赤文字 */
    .alert-text { color: #e74c3c; }
    .normal-text { color: #2c3e50; }
    
    /* スマホでの余白調整 */
    .block-container { padding-top: 2rem; padding-bottom: 4rem; }
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

# ---------------------------------------------------------
# メイン処理
# ---------------------------------------------------------

def main():
    st.markdown("### 教科書在庫管理")
    
    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None: return

    # データ前処理
    df_items.columns = df_items.columns.str.strip()
    try:
        df_items['商品ID'] = pd.to_numeric(df_items['商品ID'])
        df_items['現在在庫数'] = pd.to_numeric(df_items['現在在庫数'])
        df_items['発注点'] = pd.to_numeric(df_items['発注点'])
    except: st.warning("数値変換エラー")

    df_items = df_items.sort_values('商品ID', ascending=False)

    # 検索バーと更新ボタン
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        search_query = st.text_input("検索", placeholder="キーワードを入力", label_visibility="collapsed")
    with col_btn:
        if st.button("更新"): st.rerun()

    # フィルタリング
    if search_query:
        mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
        df_display = df_items[mask]
    else:
        df_display = df_items

    # タブ（アイコンなしのシンプルテキスト）
    tab_list, tab_add, tab_log = st.tabs(["在庫リスト", "新規登録", "履歴"])

    # --- 在庫リストタブ ---
    with tab_list:
        if df_display.empty:
            st.info("データが見つかりません")
        
        for index, row in df_display.iterrows():
            # 変数準備
            item_id = int(row['商品ID']) # Pythonのint型に変換
            name = row['教科書名']
            stock = int(row['現在在庫数'])
            alert = int(row['発注点'])
            pub = row['出版社']
            loc = row['保管場所']
            is_low = stock <= alert
            
            # カード表示（HTML生成）
            stock_color_class = "alert-text" if is_low else "normal-text"
            
            st.markdown(f"""
            <div class="item-container">
                <div class="item-header">
                    <div>
                        <div class="item-title">{name}</div>
                        <div class="item-meta">{pub} | {loc}</div>
                    </div>
                    <div style="text-align:right;">
                        <span class="stock-count {stock_color_class}">{stock}</span>
                        <span class="stock-unit">冊</span>
                        {f'<br><span style="color:#e74c3c; font-size:0.8em; font-weight:bold;">不足</span>' if is_low else ''}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 操作エリア（カードの直下に配置）
            c_input, c_in, c_out = st.columns([2, 1.5, 1.5])
            
            with c_input:
                # 数量入力（キーをユニークにする）
                qty = st.number_input("数量", min_value=1, value=10, label_visibility="collapsed", key=f"q_{item_id}")
            
            with c_in:
                # 入庫ボタン（通常のボタン）
                if st.button("入庫", key=f"in_{item_id}"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "入庫")
            
            with c_out:
                # 出庫ボタン（赤色にするためにtype="primary"を使用）
                if st.button("出庫", key=f"out_{item_id}", type="primary"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "出庫")

    # --- 新規登録タブ ---
    with tab_add:
        with st.form("add"):
            name = st.text_input("教科書名 *")
            
            existing_pubs = list(df_items['出版社'].unique()) if '出版社' in df_items.columns else []
            pub_select = st.selectbox("出版社 *", options=["選択してください"] + existing_pubs + ["その他（手入力）"])
            pub_input = ""
            if pub_select == "その他（手入力）":
                pub_input = st.text_input("出版社名を入力")
                
            c1, c2 = st.columns(2)
            isbn = c1.text_input("ISBN")
            loc = c2.text_input("保管場所")
            
            c3, c4 = st.columns(2)
            stock = c3.number_input("初期在庫 *", 0)
            alert = c4.number_input("発注点", 10)
            
            if st.form_submit_button("登録", use_container_width=True):
                final_pub = pub_input if pub_select == "その他（手入力）" else pub_select
                if not name or final_pub == "選択してください" or (pub_select == "その他（手入力）" and not pub_input):
                    st.error("必須項目を入力してください")
                else:
                    new_id = int(df_items['商品ID'].max()) + 1
                    # Pythonの基本型(int/str)に変換してからリストにする
                    new_row = [int(new_id), str(name), str(isbn), str(final_pub), int(stock), int(alert), str(loc)]
                    ws_items.append_row(new_row)
                    add_log(ws_logs, "新規登録", new_id, name, stock)
                    st.success("登録しました")
                    st.rerun()

    # --- 履歴タブ ---
    with tab_log:
        st.dataframe(df_logs, use_container_width=True)


# ---------------------------------------------------------
# ロジック関数（ログ記録の修正済み）
# ---------------------------------------------------------

def update_stock(ws_items, ws_logs, item_id, item_name, current_stock, quantity, action_type):
    # 計算
    new_stock = current_stock + quantity if action_type == "入庫" else current_stock - quantity
    if new_stock < 0:
        st.error("在庫が足りません")
        return
        
    try:
        # スプレッドシート更新
        cell = ws_items.find(str(item_id), in_column=1)
        ws_items.update_cell(cell.row, 5, new_stock)
        
        # ログ記録
        change = quantity if action_type == "入庫" else -quantity
        add_log(ws_logs, action_type, item_id, item_name, change)
        
        st.toast(f"{item_name} を {action_type} しました！") # スマホっぽい通知
        st.rerun()
    except Exception as e:
        st.error(f"エラー: {e}")

def add_log(ws_logs, action_type, item_id, item_name, change_val):
    try:
        latest = ws_logs.cell(2, 1).value
        # ここで確実に int 型に変換する
        new_log_id = int(latest) + 1 if latest and latest.isdigit() else 1
    except:
        new_log_id = 1
    
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    
    # 全てのデータを「Pythonの標準的な型（int, str）」にしてから渡す
    # これでスプレッドシートへの転記エラー（JSON serialization error）が直ります
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
