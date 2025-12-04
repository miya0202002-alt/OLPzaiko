import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定・デザイン調整（GAS/Bootstrap風デザイン再現）
# ---------------------------------------------------------

st.set_page_config(page_title="教科書在庫管理", layout="centered", initial_sidebar_state="collapsed")

# カスタムCSS：提供されたHTML/CSSをStreamlit用に移植
st.markdown("""
<style>
    /* ベースフォント（HTMLと同じHelvetica Neue） */
    body { font-family: "Helvetica Neue", Arial, sans-serif; background-color: #f8f9fa; color: #333; }
    
    /* アプリ全体のコンテナ調整 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 1000px;
    }

    /* 検索バーと更新ボタンのエリア */
    .control-panel {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    /* テーブルヘッダー（HTMLの .table-dark を再現） */
    .table-header {
        background-color: #212529; /* Bootstrap dark */
        color: #fff;
        padding: 12px 5px;
        font-weight: bold;
        font-size: 0.9em;
        border-radius: 5px 5px 0 0;
        display: flex;
        align-items: center;
    }

    /* 行のデザイン（HTMLの .table-hover を再現） */
    .row-container {
        background-color: #fff;
        border-bottom: 1px solid #dee2e6;
        border-left: 1px solid #dee2e6;
        border-right: 1px solid #dee2e6;
        padding: 10px 5px;
        display: flex;
        align-items: center;
    }
    .row-container:last-child {
        border-radius: 0 0 5px 5px;
    }

    /* 在庫不足時のスタイル（HTMLの .low-stock を再現） */
    .bg-alert { background-color: #fff3f3 !important; }
    .text-alert { color: #d63031; font-weight: bold; }
    .badge-alert {
        background-color: #dc3545;
        color: white;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.7em;
        margin-left: 5px;
    }

    /* テキストスタイル */
    .book-title { font-weight: bold; font-size: 1.0em; display: block; line-height: 1.2; }
    .book-meta { font-size: 0.8em; color: #6c757d; margin-top: 3px; display: block; }
    .stock-display { font-size: 1.2em; font-weight: bold; text-align: center; }

    /* 入力欄（数量）のデザイン */
    div[data-testid="stNumberInput"] input {
        text-align: center !important;
        padding: 5px !important;
        height: 2.2em !important;
    }
    /* ラベルを消した時の余白削除 */
    div[data-testid="stNumberInput"] { margin: 0 !important; width: 100% !important; }
    /* 上下の矢印を消す */
    button[kind="secondaryForm"] { display: none !important; }

    /* ボタンデザインの強制上書き */
    div[data-testid="column"] button {
        border-radius: 4px;
        font-weight: bold;
        border: none;
        height: 2.2em;
        width: 100%;
        padding: 0;
        font-size: 0.9em;
    }

    /* 入庫ボタン（HTMLの .btn-success #28a745 を再現） */
    /* StreamlitのSecondaryボタンを緑にする */
    button[kind="secondary"] {
        background-color: #28a745 !important;
        color: white !important;
        border: 1px solid #28a745 !important;
    }
    
    /* 出庫ボタン（HTMLの .btn-outline-danger 風だが、スマホで見やすく塗りつぶし #dc3545） */
    /* StreamlitのPrimaryボタンを赤にする */
    button[kind="primary"] {
        background-color: #dc3545 !important;
        color: white !important;
        border: 1px solid #dc3545 !important;
    }

    /* 更新ボタンだけはグレー（Bootstrap secondary）に戻す */
    div.stHorizontalBlock button[kind="secondary"] {
        background-color: #6c757d !important;
        color: white !important;
        border: 1px solid #6c757d !important;
    }
    
    /* スマホでの横並び強制（Flexbox） */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 5px !important;
    }
    div[data-testid="column"] {
        min-width: 0 !important;
        flex: 1 1 auto !important;
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
    # ヘッダー（アイコン付き）
    st.markdown("""<h2 class="mb-4">📚 教科書在庫管理</h2>""", unsafe_allow_html=True)
    
    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None: return

    # データ前処理
    df_items.columns = df_items.columns.str.strip()
    cols_to_num = ['商品ID', '現在在庫数', '発注点']
    for col in cols_to_num:
        if col in df_items.columns:
            df_items[col] = pd.to_numeric(df_items[col], errors='coerce').fillna(0).astype(int)

    # ---------------------------------------------------------
    # 操作パネル（HTMLのボタン配置を再現）
    # ---------------------------------------------------------
    c_update, c_search = st.columns([1, 4])
    with c_update:
        if st.button("↻ 更新"): st.rerun()
    with c_search:
        search_query = st.text_input("検索", placeholder="教科書名、出版社など...", label_visibility="collapsed")

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

    # タブ
    tab_list, tab_add = st.tabs(["在庫リスト", "新規登録"])

    # ---------------------------------------------------------
    # 在庫リスト（HTMLのデザインとご要望の列構成を統合）
    # ---------------------------------------------------------
    with tab_list:
        # ヘッダー行（黒背景）
        st.markdown("""
        <div class="table-header">
            <div style="flex:3.5; padding-left:5px;">教科書情報</div>
            <div style="flex:1; text-align:center;">在庫</div>
            <div style="flex:1.2; text-align:center;">数</div>
            <div style="flex:1; text-align:center;">入庫</div>
            <div style="flex:1; text-align:center;">出庫</div>
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
            bg_class = "bg-alert" if is_low else ""
            stock_color = "text-alert" if is_low else ""
            badge = '<span class="badge-alert">不足</span>' if is_low else ""

            # 1行のコンテナ
            st.markdown(f'<div class="row-container {bg_class}">', unsafe_allow_html=True)
            
            # 列レイアウト [情報, 在庫, 数, 入, 出]
            c1, c2, c3, c4, c5 = st.columns([3.5, 1, 1.2, 1, 1], gap="small")
            
            with c1:
                # 教科書情報（出版社や場所もここにまとめて省スペース化）
                st.markdown(f"""
                <div style="padding-left:5px; line-height:1.2;">
                    <span class="book-title">{name}</span>
                    <span class="book-meta">{pub} | {loc} <br> <i class="bi bi-upc"></i> {isbn}</span>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                # 在庫数
                st.markdown(f"""
                <div style="text-align:center;">
                    <span class="stock-display {stock_color}">{stock}</span>
                    {badge}
                </div>
                """, unsafe_allow_html=True)

            with c3:
                # 数量入力：初期値1固定
                qty = st.number_input("qty", min_value=1, value=1, label_visibility="collapsed", key=f"q_{item_id}")
                
            with c4:
                # 入庫（緑）
                if st.button("入", key=f"in_{item_id}"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "入庫")
            
            with c5:
                # 出庫（赤）
                if st.button("出", key=f"out_{item_id}", type="primary"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "出庫")

            st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 新規登録
    # ---------------------------------------------------------
    with tab_add:
        st.markdown("<h5><i class='bi bi-plus-circle'></i> 新しい教科書の登録</h5>", unsafe_allow_html=True)
        with st.form("add"):
            # GSSから候補を取得
            existing_names = list(df_items['教科書名'].unique()) if '教科書名' in df_items.columns else []
            name_select = st.selectbox("教科書名", options=existing_names + ["新規入力"], index=None, placeholder="教科書名を選択してください...")
            name_input = ""
            if name_select == "新規入力":
                name_input = st.text_input("新しい教科書名を入力")
            
            existing_pubs = list(df_items['出版社'].unique()) if '出版社' in df_items.columns else []
            pub_select = st.selectbox("出版社", options=existing_pubs + ["その他"], index=None, placeholder="出版社を選択してください...")
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
        change = quantity if action_type == "入庫" else -quantity
        add_log(ws_logs, action_type, item_id, item_name, change)
        st.toast(f"{action_type}完了！ (現在: {new_stock}冊)")
        st.rerun()
    except Exception as e:
        st.error(f"エラー: {e}")

def add_log(ws_logs, action_type, item_id, item_name, change_val):
    try:
        all_vals = ws_logs.col_values(1)
        if len(all_vals) > 1:
            last_id = all_vals[-1]
            new_log_id = int(last_id) + 1 if str(last_id).isdigit() else 1
        else:
            new_log_id = 1
        now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        row_data = [int(new_log_id), str(now), str(action_type), int(item_id), int(change_val), str(item_name)]
        # append_row を使用して確実に記録
        ws_logs.append_row(row_data)
    except Exception as e:
        st.error(f"ログ記録エラー: {e}")

if __name__ == "__main__":
    main()
