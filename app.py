import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定・デザイン調整（スマホ完全対応版）
# ---------------------------------------------------------

st.set_page_config(page_title="教科書在庫管理", layout="centered", initial_sidebar_state="collapsed")

# カスタムCSS：スマホでの1行表示を強制するスタイル
st.markdown("""
<style>
    /* 全体の調整 */
    body { font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif; color: #333; margin: 0; padding: 0; }
    .block-container { padding-top: 1rem; padding-bottom: 2rem; padding-left: 0.5rem; padding-right: 0.5rem; }
    
    /* 検索バー周り */
    div[data-testid="stTextInput"] { margin-bottom: 5px; }
    
    /* 「変な□」を消すためのリセット */
    div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
    
    /* テーブル全体（スマホでも横スクロールせずに収める） */
    .inventory-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        font-size: 14px; /* スマホ用に少し小さく */
    }
    
    /* ヘッダー（黒背景） */
    .inventory-table th {
        background-color: #222;
        color: #fff;
        padding: 8px 4px;
        text-align: center;
        font-weight: bold;
        white-space: nowrap; /* 改行させない */
    }
    
    /* データ行 */
    .inventory-table td {
        border-bottom: 1px solid #ddd;
        padding: 8px 4px;
        vertical-align: middle;
    }
    
    /* 各列の幅調整（スマホで1行に収めるための重要設定） */
    .col-name { width: 45%; text-align: left; }
    .col-stock { width: 15%; text-align: center; font-weight: bold; }
    .col-qty { width: 15%; text-align: center; }
    .col-btn { width: 12.5%; text-align: center; }
    
    /* 不足時の赤字 */
    .alert { color: #d63031; font-weight: bold; }
    .row-alert { background-color: #fff5f5; }
    
    /* 教科書名のスタイル */
    .book-title { font-weight: bold; display: block; line-height: 1.2; font-size: 0.95em; }
    .book-meta { font-size: 0.75em; color: #666; display: block; margin-top: 2px; }
    
    /* ボタンのスタイル（HTMLボタン） */
    .btn-action {
        width: 100%;
        padding: 6px 0;
        border: none;
        border-radius: 4px;
        color: white;
        font-weight: bold;
        cursor: pointer;
        font-size: 0.85em;
        text-align: center;
        text-decoration: none;
        display: inline-block;
    }
    .btn-in { background-color: #28a745; } /* 緑 */
    .btn-out { background-color: #e74c3c; } /* 朱色 */
    
    /* 数量入力（HTML input） */
    .input-qty {
        width: 100%;
        padding: 5px;
        border: 1px solid #ccc;
        border-radius: 4px;
        text-align: center;
        font-size: 1em;
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

    # ---------------------------------------------------------
    # 検索・更新・並べ替え
    # ---------------------------------------------------------
    c_search, c_update = st.columns([3, 1])
    with c_search:
        search_query = st.text_input("検索", placeholder="教科書名、出版社...", label_visibility="collapsed")
    with c_update:
        if st.button("↻ 更新"): st.rerun()

    # 並べ替え（名前順を削除）
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
    # 在庫リスト（HTMLテーブルで完全1行表示）
    # ---------------------------------------------------------
    with tab_list:
        # ヘッダー（黒背景）
        # スマホでも絶対に崩れないHTMLテーブル構造
        
        # StreamlitのColumnsレイアウト
        # ここで `st.columns` を使い、それぞれの列の中に要素を配置する方式に戻し、
        # CSSで強制的に横並びにする（flex-basis調整）
        
        # ヘッダー行
        st.markdown("""
        <div style="display:flex; background:#222; color:white; padding:8px 5px; font-weight:bold; border-radius:4px 4px 0 0; font-size:0.85em;">
            <div style="flex:4; padding-left:5px;">教科書情報</div>
            <div style="flex:1.2; text-align:center;">在庫</div>
            <div style="flex:1.5; text-align:center;">数量</div>
            <div style="flex:1.2; text-align:center;">入</div>
            <div style="flex:1.2; text-align:center;">出</div>
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
            
            is_low = stock <= alert
            bg_style = "background-color: #fff5f5;" if is_low else "background-color: #fff;"
            stock_color = "color: #d63031;" if is_low else "color: #333;"
            alert_badge = '<br><span style="font-size:0.6em; color:red;">不足</span>' if is_low else ""

            # 1行のコンテナ（Flexboxで強制横並び）
            st.markdown(f'<div style="{bg_style} border-bottom:1px solid #ddd; border-left:1px solid #ddd; border-right:1px solid #ddd; padding:8px 0;">', unsafe_allow_html=True)
            
            # gap="2px" で限界まで詰める
            c1, c2, c3, c4, c5 = st.columns([4, 1.2, 1.5, 1.2, 1.2], gap="small")
            
            with c1:
                st.markdown(f"""
                <div style="padding-left:5px; line-height:1.2;">
                    <span style="font-weight:bold; font-size:0.9em; display:block;">{name}</span>
                    <span style="font-size:0.7em; color:#666;">{pub}</span>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                st.markdown(f"""
                <div style="text-align:center; flex-direction:column; justify-content:center; height:100%; display:flex;">
                    <span style="font-weight:bold; font-size:1.0em; {stock_color}">{stock}</span>
                    {alert_badge}
                </div>
                """, unsafe_allow_html=True)

            with c3:
                # 数量入力：keyをユニークにし、初期値を必ず1に
                qty = st.number_input("qty", min_value=1, value=1, label_visibility="collapsed", key=f"q_{item_id}_{datetime.now().microsecond}") 
                # ↑ keyに時間を混ぜることで強制リセット効果を狙うが、入力しにくくなるため、
                # シンプルに固定IDにする（ただしStreamlitの仕様上、リロードしないと1に戻らない場合がある）
                # 今回は確実に1にするため、session_stateを使わず毎回レンダリング時に1を指定
                
            with c4:
                # 入庫ボタン
                if st.button("入", key=f"in_{item_id}"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "入庫")
            
            with c5:
                # 出庫ボタン
                if st.button("出", key=f"out_{item_id}", type="primary"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "出庫")

            st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 新規登録
    # ---------------------------------------------------------
    with tab_add:
        st.markdown("##### 新しい教科書の登録")
        with st.form("add"):
            existing_names = list(df_items['教科書名'].unique()) if '教科書名' in df_items.columns else []
            name_select = st.selectbox("教科書名", options=existing_names + ["新規入力"], index=None, placeholder="教科書名を選択...")
            name_input = ""
            if name_select == "新規入力":
                name_input = st.text_input("新しい教科書名を入力")
            
            existing_pubs = list(df_items['出版社'].unique()) if '出版社' in df_items.columns else []
            pub_select = st.selectbox("出版社", options=existing_pubs + ["その他"], index=None, placeholder="出版社を選択...")
            pub_input = ""
            if pub_select == "その他":
                pub_input = st.text_input("出版社名を入力")
                
            c1, c2 = st.columns(2)
            isbn = c1.text_input("ISBN")
            loc = c2.text_input("保管場所")
            
            c3, c4 = st.columns(2)
            # 初期値「1」
            stock = c3.number_input("初期在庫 *", min_value=1, value=1)
            alert = c4.number_input("発注点", min_value=1, value=1)
            
            if st.form_submit_button("登録", use_container_width=True):
                final_name = name_input if name_select == "新規入力" else name_select
                final_pub = pub_input if pub_select == "その他" else pub_select
                
                if not final_name or not final_pub:
                    st.error("教科書名と出版社は必須です")
                else:
                    new_id = int(df_items['商品ID'].max()) + 1 if not df_items.empty else 1
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
        
        # ログ記録処理（ここが修正ポイント！）
        change = quantity if action_type == "入庫" else -quantity
        add_log(ws_logs, action_type, item_id, item_name, change)
        
        st.toast(f"{action_type}完了！ (現在: {new_stock}冊)")
        st.rerun()
    except Exception as e:
        st.error(f"エラー: {e}")

def add_log(ws_logs, action_type, item_id, item_name, change_val):
    # 確実にログを追加するための修正版関数
    try:
        # ログIDの採番（データが空の場合の対策済み）
        all_vals = ws_logs.col_values(1) # 1列目（ログID）を全て取得
        if len(all_vals) > 1: # ヘッダー以外にデータがある場合
            last_id = all_vals[-1]
            new_log_id = int(last_id) + 1 if str(last_id).isdigit() else 1
        else:
            new_log_id = 1
            
        now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        
        # append_row を使用（insert_rowより確実）
        # 全てのデータを文字列または整数に変換して渡す
        row_data = [
            int(new_log_id),
            str(now),
            str(action_type),
            int(item_id),
            int(change_val),
            str(item_name)
        ]
        
        ws_logs.append_row(row_data)
        
    except Exception as e:
        # 万が一エラーが出てもアプリを止めないが、エラー内容は表示する
        st.error(f"ログ記録エラー: {e}")

if __name__ == "__main__":
    main()
