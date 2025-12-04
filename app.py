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

# カスタムCSS：スマホ最適化・枠線削除・メリハリ調整
st.markdown("""
<style>
    /* 全体の調整 */
    body { font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif; color: #333; }
    
    /* 「変な□」の原因だった枠線を削除し、フラットなデザインに */
    .main-container { padding: 10px; }
    
    /* 検索バー周り：青枠はやめてシンプルに見やすく */
    div[data-testid="stTextInput"] { margin-bottom: 0px; }
    
    /* テーブルヘッダー（GAS風 黒背景） - スマホでも崩れないように調整 */
    .table-header {
        background-color: #222;
        color: #fff;
        padding: 8px 5px;
        font-weight: bold;
        font-size: 0.85em; /* スマホ用に少し小さく */
        border-radius: 4px 4px 0 0;
        margin-top: 10px;
        display: flex;
        align-items: center;
    }

    /* 1行レイアウトのスタイル - 区切り線を追加 */
    .row-container {
        border-bottom: 1px solid #ddd;
        border-left: 1px solid #ddd;
        border-right: 1px solid #ddd;
        padding: 8px 2px; /* 上下パディングを減らす */
        background-color: #fff;
    }
    .row-container:last-child {
        border-radius: 0 0 4px 4px;
    }

    /* 文字のメリハリと区切り線 */
    .col-border {
        border-right: 1px solid #eee; /* 縦線を追加 */
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .text-title { font-size: 1.0em; font-weight: bold; color: #000; line-height: 1.2; }
    .text-sub { font-size: 0.75em; color: #888; display: block; margin-top: 2px; }
    .text-stock { font-size: 1.2em; font-weight: bold; }
    .text-alert { color: #d63031; }

    /* ボタンのデザイン調整：高さを揃える */
    div[data-testid="column"] button {
        padding: 0px 5px !important;
        min-height: 2.2em !important;
        height: 2.2em !important;
        font-size: 0.85em !important;
        line-height: 1 !important;
    }
    
    /* 入庫ボタン（緑） */
    button[kind="secondary"] {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
    }
    /* 更新ボタンだけはグレーに戻す */
    div.stHorizontalBlock button[kind="secondary"] {
        background-color: #f0f0f0 !important;
        color: #333 !important;
        border: 1px solid #ccc !important;
    }
    
    /* 入力欄（数量）の調整 */
    div[data-testid="stNumberInput"] input {
        padding: 5px !important;
        height: 2.2em !important;
        text-align: center !important;
    }
    /* ラベルを消した時の余白を詰める */
    div[data-testid="stNumberInput"] { margin-top: -15px; }

    /* スマホでのカラム間隔を詰める */
    [data-testid="column"] { padding: 0 2px !important; }
    
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
        # ログがない場合のエラー回避
        if not logs_data:
            df_logs = pd.DataFrame(columns=['ログID', '日時', '操作', '商品ID', '変動数', '備考'])
        else:
            df_logs = pd.DataFrame(logs_data[1:], columns=logs_data[0])
        
        return sh, ws_items, df_items, ws_logs, df_logs
    except Exception as e:
        st.error(f"接続エラー: {e}")
        return None, None, None, None, None

def main():
    # ヘッダー（画像なし、シンプルにタイトルのみ）
    st.markdown("### 教科書在庫管理")
    
    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None: return

    # データ前処理
    df_items.columns = df_items.columns.str.strip()
    cols_to_num = ['商品ID', '現在在庫数', '発注点']
    for col in cols_to_num:
        if col in df_items.columns:
            df_items[col] = pd.to_numeric(df_items[col], errors='coerce').fillna(0).astype(int)

    # 検索・更新・並べ替え
    c_search, c_update = st.columns([3, 1])
    with c_search:
        search_query = st.text_input("検索", placeholder="教科書名、出版社...", label_visibility="collapsed")
    with c_update:
        if st.button("↻ 更新"): st.rerun()

    sort_mode = st.radio("", ["追加日順", "在庫少ない順", "名前順"], horizontal=True, label_visibility="collapsed")
    
    if sort_mode == "追加日順":
        if '商品ID' in df_items.columns: df_items = df_items.sort_values('商品ID', ascending=False)
    elif sort_mode == "在庫少ない順":
        df_items = df_items.sort_values('現在在庫数', ascending=True)
    elif sort_mode == "名前順":
        df_items = df_items.sort_values('教科書名', ascending=True)

    # フィルタリング
    if search_query:
        mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
        df_display = df_items[mask]
    else:
        df_display = df_items

    # タブ
    tab_list, tab_add = st.tabs(["📦 在庫リスト", "➕ 新規登録"])

    # ---------------------------------------------------------
    # 在庫リスト（スマホ完全対応版）
    # ---------------------------------------------------------
    with tab_list:
        # ヘッダー行（Flexboxで比率調整）
        st.markdown("""
        <div class="table-header">
            <div style="width:40%; padding-left:5px;">教科書情報</div>
            <div style="width:15%; text-align:center;">在庫</div>
            <div style="width:15%; text-align:center;">数量</div>
            <div style="width:15%; text-align:center;">入庫</div>
            <div style="width:15%; text-align:center;">出庫</div>
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
            bg_style = "background-color: #fff5f5;" if is_low else "" 
            stock_color = "text-alert" if is_low else ""

            # 行の開始
            st.markdown(f'<div class="row-container" style="{bg_style}">', unsafe_allow_html=True)
            
            # カラム比率：スマホの狭い画面に合わせて調整
            # gap="small" で余白を削る
            c1, c2, c3, c4, c5 = st.columns([4, 1.5, 1.5, 1.5, 1.5], gap="small")
            
            with c1:
                # 教科書情報
                st.markdown(f"""
                <div style="padding-right:5px; border-right:1px solid #eee; height:100%;">
                    <div class="text-title">{name}</div>
                    <span class="text-sub">{pub}</span>
                </div>
                """, unsafe_allow_html=True)
                
            with c2:
                # 在庫数
                st.markdown(f"""
                <div class="col-border" style="flex-direction:column;">
                    <span class="text-stock {stock_color}">{stock}</span>
                    {f'<span style="font-size:0.6em; color:red;">不足</span>' if is_low else ''}
                </div>
                """, unsafe_allow_html=True)
                
            with c3:
                # 数量入力：初期値を「1」に固定
                # label_visibility="collapsed" でラベルを消してスペース確保
                qty = st.number_input("qty", min_value=1, value=1, label_visibility="collapsed", key=f"q_{item_id}")
                
            with c4:
                # 入庫
                if st.button("入", key=f"in_{item_id}"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "入庫")
                    
            with c5:
                # 出庫
                if st.button("出", key=f"out_{item_id}", type="primary"):
                    update_stock(ws_items, ws_logs, item_id, name, stock, qty, "出庫")

            st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 新規登録（初期値修正済み）
    # ---------------------------------------------------------
    with tab_add:
        st.markdown("##### 新しい教科書の登録")
        with st.form("add"):
            # プレースホルダーを薄い文字で表現
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
            # 初期値を「1」に設定！
            stock = c3.number_input("初期在庫 *", min_value=1, value=1)
            alert = c4.number_input("発注点", min_value=1, value=1)
            
            if st.form_submit_button("登録", use_container_width=True):
                final_name = name_input if name_select == "新規入力" else name_select
                final_pub = pub_input if pub_select == "その他" else pub_select
                
                if not final_name or not final_pub:
                    st.error("教科書名と出版社は必須です")
                else:
                    new_id = int(df_items['商品ID'].max()) + 1 if not df_items.empty else 1
                    # データをリスト化
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
    # 確実に追加するために append_row を使用
    try:
        # ログIDの採番（最終行を取得）
        all_logs = ws_logs.get_all_values()
        if len(all_logs) > 1:
            last_id = all_logs[-1][0] # 最後の行の1列目
            new_log_id = int(last_id) + 1 if str(last_id).isdigit() else 1
        else:
            new_log_id = 1
    except:
        new_log_id = 1
    
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    
    # Python標準型に変換して追加
    row_data = [
        int(new_log_id),
        str(now),
        str(action_type),
        int(item_id),
        int(change_val),
        str(item_name)
    ]
    
    # append_row で一番下に追加（これが一番エラーが出にくい）
    ws_logs.append_row(row_data)

if __name__ == "__main__":
    main()
