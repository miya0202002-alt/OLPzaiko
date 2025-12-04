import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定・デザイン調整（Apple風モダンUI）
# ---------------------------------------------------------

st.set_page_config(page_title="教科書在庫管理", layout="centered", initial_sidebar_state="collapsed")

# カスタムCSS
st.markdown("""
<style>
    /* 全体のフォント：Apple風のSan Francisco / Helvetica Neue */
    body { font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "Segoe UI", Arial, sans-serif; color: #1d1d1f; }
    
    /* ボタンのスタイル */
    div.stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: 500;
        height: 2.4em;
        border: none;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
    }
    div.stButton > button:hover { transform: scale(1.02); }
    
    /* 更新ボタン */
    div[data-testid="stHorizontalBlock"] button {
        background-color: #f5f5f7;
        color: #1d1d1f;
        border: 1px solid #d2d2d7;
    }

    /* テーブルヘッダー（GAS風の黒背景） */
    .table-header {
        background-color: #1d1d1f;
        color: #f5f5f7;
        padding: 12px 15px;
        border-radius: 8px 8px 0 0;
        display: flex;
        justify-content: space-between;
        font-weight: bold;
        font-size: 0.9em;
        margin-top: 20px;
    }

    /* アイテム行のデザイン */
    .item-row {
        background-color: #ffffff;
        border-bottom: 1px solid #d2d2d7;
        border-left: 1px solid #d2d2d7;
        border-right: 1px solid #d2d2d7;
        padding: 15px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .item-row:last-child {
        border-radius: 0 0 8px 8px;
    }
    
    /* 在庫不足時のハイライト */
    .bg-alert { background-color: #fff2f2; }
    .text-alert { color: #d63031; font-weight: bold; }
    
    /* 入力欄の調整 */
    input[type="number"] { padding: 5px; border-radius: 4px; border: 1px solid #d2d2d7; }
    
    /* タイトル周りのレイアウト */
    .header-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .app-title { font-size: 1.8em; font-weight: 700; color: #1d1d1f; margin: 0; }
    
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
    # --- ヘッダーエリア（ロゴとタイトル） ---
    # ※ロゴを表示したい場合は、GitHubに画像をアップロードして 'logo.png' の部分を書き換えてください
    # st.image("logo.png", width=50) 
    st.markdown('<div class="header-container"><div class="app-title">教科書在庫管理</div></div>', unsafe_allow_html=True)

    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None: return

    # データ前処理
    df_items.columns = df_items.columns.str.strip()
    cols_to_num = ['商品ID', '現在在庫数', '発注点']
    for col in cols_to_num:
        if col in df_items.columns:
            df_items[col] = pd.to_numeric(df_items[col], errors='coerce').fillna(0).astype(int)

    if '商品ID' in df_items.columns:
        df_items = df_items.sort_values('商品ID', ascending=False)

    # 検索と更新
    c_search, c_update = st.columns([4, 1])
    with c_search:
        search_query = st.text_input("検索", placeholder="教科書名、出版社など...", label_visibility="collapsed")
    with c_update:
        if st.button("↻ 更新"): st.rerun()

    # フィルタリング
    if search_query:
        mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
        df_display = df_items[mask]
    else:
        df_display = df_items

    # タブ切り替え（履歴タブは削除しました）
    tab_list, tab_add = st.tabs(["在庫リスト", "新規登録"])

    # --- 在庫リストタブ（GAS風デザイン） ---
    with tab_list:
        # 黒背景のヘッダーバー
        st.markdown("""
        <div class="table-header">
            <div style="flex:2;">教科書情報</div>
            <div style="flex:1; text-align:center;">在庫</div>
            <div style="flex:1.5; text-align:right;">操作</div>
        </div>
        """, unsafe_allow_html=True)

        if df_display.empty:
            st.info("該当する教科書がありません")
        
        for index, row in df_display.iterrows():
            item_id = row['商品ID']
            name = row['教科書名']
            stock = row['現在在庫数']
            alert = row['発注点']
            pub = row['出版社']
            loc = row['保管場所']
            isbn = row.get('ISBNコード', '-') # 列がない場合の安全策
            
            is_low = stock <= alert
            row_bg = "bg-alert" if is_low else ""
            stock_style = "text-alert" if is_low else ""

            # 行の開始（HTMLコンテナ）
            st.markdown(f"""
            <div class="item-row {row_bg}">
                <div style="display:flex; justify-content:space-between; align-items:start;">
                    <div style="flex:2;">
                        <div style="font-weight:bold; font-size:1.1em; color:#1d1d1f;">{name}</div>
                        <div style="font-size:0.8em; color:#86868b; margin-top:2px;">{pub} <span style="margin:0 5px;">|</span> {loc}</div>
                        <div style="font-size:0.7em; color:#a1a1a6;">{isbn}</div>
                    </div>
                    <div style="flex:1; text-align:center;">
                        <div style="font-size:1.4em; font-weight:bold;" class="{stock_style}">{stock}</div>
                        <div style="font-size:0.7em; color:#86868b;">冊</div>
                        {f'<div style="font-size:0.7em; background:#ff3b30; color:white; padding:2px 6px; border-radius:4px; display:inline-block; margin-top:4px;">不足</div>' if is_low else ''}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # 操作ボタンエリア（行の中に配置）
            # Streamlitのcolumnを使って配置
            c_qty, c_in, c_out = st.columns([1.5, 1, 1])
            with c_qty:
                # 初期値を1に変更
                qty = st.number_input("数量", min_value=1, value=1, label_visibility="collapsed", key=f"q_{item_id}")
            with c_in:
                # 緑ボタン
                if st.button("入庫", key=f"in_{item_id}"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "入庫")
            with c_out:
                # 赤ボタン（primary）
                if st.button("出庫", key=f"out_{item_id}", type="primary"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "出庫")
            
            # 行の終わり
            st.markdown("</div>", unsafe_allow_html=True)

    # --- 新規登録タブ ---
    with tab_add:
        st.markdown("##### 新しい教科書の登録")
        with st.form("add"):
            # 教科書名の候補機能（サジェスト）
            existing_names = list(df_items['教科書名'].unique()) if '教科書名' in df_items.columns else []
            name_select = st.selectbox("教科書名（候補から選択、または手入力）", options=["選択/入力してください"] + existing_names + ["新規入力"])
            
            name_input = ""
            if name_select == "新規入力":
                name_input = st.text_input("新しい教科書名を入力")
            
            # 出版社
            existing_pubs = list(df_items['出版社'].unique()) if '出版社' in df_items.columns else []
            pub_select = st.selectbox("出版社", options=["選択してください"] + existing_pubs + ["その他（手入力）"])
            pub_input = ""
            if pub_select == "その他（手入力）":
                pub_input = st.text_input("出版社名を入力")
                
            c1, c2 = st.columns(2)
            isbn = c1.text_input("ISBN (任意)")
            loc = c2.text_input("保管場所 (任意)")
            
            c3, c4 = st.columns(2)
            stock = c3.number_input("初期在庫 *", min_value=0, value=0)
            alert = c4.number_input("発注点", min_value=0, value=10)
            
            if st.form_submit_button("登録", use_container_width=True):
                # 入力値の決定
                final_name = name_input if name_select == "新規入力" else name_select
                final_pub = pub_input if pub_select == "その他（手入力）" else pub_select
                
                if final_name == "選択/入力してください" or not final_name:
                    st.error("教科書名は必須です")
                elif final_pub == "選択してください" or not final_pub:
                    st.error("出版社は必須です")
                else:
                    new_id = int(df_items['商品ID'].max()) + 1
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
        latest = ws_logs.cell(2, 1).value
        new_log_id = int(latest) + 1 if latest and latest.isdigit() else 1
    except: new_log_id = 1
    
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    row_data = [int(new_log_id), str(now), str(action_type), int(item_id), int(change_val), str(item_name)]
    ws_logs.insert_row(row_data, index=2)

if __name__ == "__main__":
    main()
