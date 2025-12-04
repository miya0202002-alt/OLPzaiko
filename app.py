import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定・接続部分
# ---------------------------------------------------------

# スマホで見やすいように「ワイドモード」ではなく、デフォルトの幅を使用しつつタイトル設定
st.set_page_config(page_title="教科書在庫管理", layout="centered", initial_sidebar_state="collapsed")

# カスタムCSSでデザインをGAS版＆モダン風に調整
st.markdown("""
<style>
    /* 全体のフォント調整 */
    body { font-family: "Helvetica Neue", Arial, sans-serif; }
    
    /* ボタンの色をカスタマイズ */
    div.stButton > button:first-child {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        height: 3em;
    }
    /* 入庫ボタン風（緑） */
    .in-btn button {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
    }
    /* 出庫ボタン風（赤） */
    .out-btn button {
        background-color: #dc3545 !important;
        color: white !important;
        border: none !important;
    }
    
    /* 在庫不足のアラート表示 */
    .low-stock {
        background-color: #ffe6e6;
        color: #cc0000;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        font-size: 0.9em;
        display: inline-block;
        margin-left: 5px;
    }
    
    /* カード風のリスト表示 */
    .item-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 10px;
        border-left: 5px solid #6c757d;
    }
    .card-low { border-left-color: #dc3545; background-color: #fff8f8; }
    .card-ok { border-left-color: #28a745; }
    
    /* タイトル周りをスッキリさせる */
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    
    /* スマホでの入力欄の視認性向上 */
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
    st.markdown("### 📚 教科書在庫管理")
    
    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None: return

    # データの前処理
    df_items.columns = df_items.columns.str.strip()
    try:
        df_items['商品ID'] = pd.to_numeric(df_items['商品ID'])
        df_items['現在在庫数'] = pd.to_numeric(df_items['現在在庫数'])
        df_items['発注点'] = pd.to_numeric(df_items['発注点'])
    except: st.warning("数値変換エラー")

    df_items = df_items.sort_values('商品ID', ascending=False)

    # 上部に検索バーを配置（スマホでもアクセスしやすい）
    col_search, col_reload = st.columns([4, 1])
    with col_search:
        search_query = st.text_input("🔍", placeholder="教科書名・出版社で検索...", label_visibility="collapsed")
    with col_reload:
        if st.button("🔄"): st.rerun()

    # フィルタリング
    if search_query:
        mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
        df_display = df_items[mask]
    else:
        df_display = df_items

    # タブ切り替え（モダンな感じに）
    tab_list, tab_add, tab_log = st.tabs(["📦 在庫リスト", "➕ 新規登録", "📜 履歴"])

    # --- 在庫リストタブ ---
    with tab_list:
        # カード型レイアウトで表示（スマホで見やすい縦長デザイン）
        for index, row in df_display.iterrows():
            stock = row['現在在庫数']
            alert = row['発注点']
            is_low = stock <= alert
            card_class = "card-low" if is_low else "card-ok"
            
            # HTMLとCSSでカードを描画
            st.markdown(f"""
            <div class="item-card {card_class}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:bold; font-size:1.1em;">{row['教科書名']}</div>
                        <div style="color:#666; font-size:0.8em;">{row['出版社']} | {row['保管場所']}</div>
                        <div style="color:#999; font-size:0.7em;">ISBN: {row['ISBNコード']}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.5em; font-weight:bold; color:{'#dc3545' if is_low else '#333'}">
                            {stock}<span style="font-size:0.6em">冊</span>
                        </div>
                        {f'<div class="low-stock">不足</div>' if is_low else ''}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 操作ボタン（アコーディオンの中に隠さず、直下に配置して1タップで開けるように）
            with st.expander(f"操作パネル: {row['教科書名']}"):
                c1, c2 = st.columns(2)
                quantity = st.number_input("数量", min_value=1, value=10, key=f"qty_{row['商品ID']}")
                
                # ボタンのデザインをCSSクラスで適用
                col_in, col_out = st.columns(2)
                with col_in:
                    st.markdown('<div class="in-btn">', unsafe_allow_html=True)
                    if st.button("入庫", key=f"in_{row['商品ID']}"):
                        update_stock(ws_items, ws_logs, row['商品ID'], row['教科書名'], stock, quantity, "入庫")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col_out:
                    st.markdown('<div class="out-btn">', unsafe_allow_html=True)
                    if st.button("出庫", key=f"out_{row['商品ID']}"):
                        update_stock(ws_items, ws_logs, row['商品ID'], row['教科書名'], stock, quantity, "出庫")
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- 新規登録タブ ---
    with tab_add:
        with st.form("add"):
            name = st.text_input("教科書名 *")
            
            # 出版社の候補リスト
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
            
            if st.form_submit_button("登録する", use_container_width=True):
                final_pub = pub_input if pub_select == "その他（手入力）" else pub_select
                if not name or final_pub == "選択してください" or (pub_select == "その他（手入力）" and not pub_input):
                    st.error("教科書名と出版社は必須です")
                else:
                    new_id = int(df_items['商品ID'].max()) + 1
                    ws_items.append_row([new_id, name, isbn, final_pub, stock, alert, loc])
                    add_log(ws_logs, "新規登録", new_id, name, stock)
                    st.success("登録完了！")
                    st.rerun()

    # --- 履歴タブ ---
    with tab_log:
        st.dataframe(df_logs, use_container_width=True)

def update_stock(ws_items, ws_logs, item_id, item_name, current_stock, quantity, action_type):
    new_stock = current_stock + quantity if action_type == "入庫" else current_stock - quantity
    if new_stock < 0:
        st.error("在庫が足りません！")
        return
        
    try:
        cell = ws_items.find(str(item_id), in_column=1)
        ws_items.update_cell(cell.row, 5, new_stock)
        
        change = quantity if action_type == "入庫" else -quantity
        add_log(ws_logs, action_type, item_id, item_name, change)
        
        st.success(f"{action_type}完了！")
        st.rerun()
    except Exception as e:
        st.error(f"エラー: {e}")

def add_log(ws_logs, action_type, item_id, item_name, change_val):
    try:
        latest = ws_logs.cell(2, 1).value
        new_id = int(latest) + 1 if latest and latest.isdigit() else 1
    except: new_id = 1
    
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    ws_logs.insert_row([new_id, now, action_type, item_id, change_val, item_name], 2)

if __name__ == "__main__":
    main()
