import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------------------------------------------------------
# 設定・接続部分
# ---------------------------------------------------------

# ページ設定（スマホ対応）
st.set_page_config(page_title="教科書在庫管理", layout="wide")

# JSONキーファイルの読み込み
# ★重要：フォルダに入れたJSONファイル名に合わせて書き換えてください
JSON_FILE = 'secret_key.json' 
SPREADSHEET_NAME = '在庫管理システム' # スプレッドシートの名前

# Google Sheetsへの接続関数
@st.cache_resource
def get_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    # ローカル実行用の設定
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
    client = gspread.authorize(creds)
    return client

# データ取得関数
def load_data():
    client = get_connection()
    try:
        sh = client.open(SPREADSHEET_NAME)
        # 商品マスタ
        ws_items = sh.worksheet('商品マスタ')
        items_data = ws_items.get_all_values()
        df_items = pd.DataFrame(items_data[1:], columns=items_data[0])
        
        # 入出庫履歴
        ws_logs = sh.worksheet('入出庫履歴')
        logs_data = ws_logs.get_all_values()
        df_logs = pd.DataFrame(logs_data[1:], columns=logs_data[0])
        
        return sh, ws_items, df_items, ws_logs, df_logs
    except Exception as e:
        st.error(f"スプレッドシートへの接続エラー: {e}")
        return None, None, None, None, None

# ---------------------------------------------------------
# メイン画面処理
# ---------------------------------------------------------

def main():
    st.title("📚 教科書在庫管理システム")

    # データの読み込み
    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None:
        return

    # 数値変換とソート
    try:
        # IDを数値にして降順（新しい順）に並べ替え
        df_items['商品ID'] = pd.to_numeric(df_items['商品ID'])
        df_items['現在在庫数'] = pd.to_numeric(df_items['現在在庫数'])
        df_items['発注点'] = pd.to_numeric(df_items['発注点'])
        df_items = df_items.sort_values('商品ID', ascending=False)
    except:
        pass

    # タブ設定
    tab1, tab2, tab3 = st.tabs(["📋 在庫一覧・操作", "➕ 新規登録", "📜 履歴ログ"])

    # ==========================================
    # タブ1: 在庫一覧・操作
    # ==========================================
    with tab1:
        # 検索バー
        col1, col2 = st.columns([3, 1])
        search_query = col1.text_input("🔍 検索", placeholder="教科書名、出版社など...")
        if col2.button("🔄 更新"):
            st.rerun()

        # フィルタリング
        if search_query:
            mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
            df_display = df_items[mask]
        else:
            df_display = df_items

        # --- 操作エリア（スマホで見やすい配置） ---
        with st.expander("📦 入庫・出庫操作パネル", expanded=True):
            # 教科書選択リスト（ID:名前）
            item_options = {f"{row['商品ID']}: {row['教科書名']}": row['商品ID'] for _, row in df_items.iterrows()}
            selected_label = st.selectbox("教科書を選択", options=list(item_options.keys()))
            
            if selected_label:
                sel_id = item_options[selected_label]
                # 選択した商品の現在の情報を取得
                current_item = df_items[df_items['商品ID'] == sel_id].iloc[0]
                
                c1, c2, c3 = st.columns(3)
                c1.metric("現在在庫", f"{current_item['現在在庫数']} 冊")
                
                action = c2.radio("操作", ["入庫", "出庫"], horizontal=True)
                qty = c3.number_input("数量", min_value=1, value=10 if action=="入庫" else 1)
                
                if st.button("実行する", type="primary", use_container_width=True):
                    update_stock(ws_items, ws_logs, sel_id, current_item['教科書名'], current_item['現在在庫数'], qty, action)

        # --- 一覧表 ---
        st.subheader("在庫リスト")
        # 在庫不足を赤くする設定
        def highlight_stock(row):
            try:
                if int(row['現在在庫数']) <= int(row['発注点']):
                    return ['background-color: #ffe6e6; color: #cc0000'] * len(row)
            except:
                pass
            return [''] * len(row)

        display_cols = ['教科書名', '出版社', '現在在庫数', '保管場所', 'ISBNコード']
        st.dataframe(
            df_display[display_cols].style.apply(highlight_stock, axis=1),
            use_container_width=True,
            height=400
        )

    # ==========================================
    # タブ2: 新規登録
    # ==========================================
    with tab2:
        st.subheader("新しい教科書の登録")
        with st.form("add_form"):
            name = st.text_input("教科書名 *")
            
            # 出版社候補
            pubs = list(df_items['出版社'].unique())
            pub = st.selectbox("出版社 *", options=pubs + ["(手入力)"])
            if pub == "(手入力)":
                pub = st.text_input("出版社名を入力")
            
            isbn = st.text_input("ISBN (任意)")
            
            c1, c2, c3 = st.columns(3)
            stock = c1.number_input("初期在庫 *", min_value=0)
            alert = c2.number_input("発注点", value=10)
            loc = c3.text_input("保管場所 (任意)")
            
            if st.form_submit_button("登録"):
                if not name or not pub:
                    st.error("教科書名と出版社は必須です")
                else:
                    add_new_item(ws_items, ws_logs, df_items, name, pub, isbn, stock, alert, loc)

    # ==========================================
    # タブ3: 履歴ログ
    # ==========================================
    with tab3:
        st.subheader("入出庫履歴")
        # ログもID順（新しい順）に
        try:
            df_logs['ログID'] = pd.to_numeric(df_logs['ログID'])
            df_logs = df_logs.sort_values('ログID', ascending=False)
        except:
            pass
        st.dataframe(df_logs, use_container_width=True)

# ---------------------------------------------------------
# ロジック関数
# ---------------------------------------------------------
def update_stock(ws_items, ws_logs, item_id, item_name, current, qty, action):
    try:
        new_stock = current + qty if action == "入庫" else current - qty
        if new_stock < 0:
            st.error("在庫が足りません！")
            return

        # スプレッドシート更新（ID検索）
        cell = ws_items.find(str(item_id), in_column=1)
        if cell:
            ws_items.update_cell(cell.row, 5, new_stock) # 5列目=在庫
            add_log(ws_logs, action, item_id, item_name, qty if action=="入庫" else -qty)
            st.success("完了しました！")
            st.rerun()
    except Exception as e:
        st.error(f"エラー: {e}")

def add_new_item(ws_items, ws_logs, df_items, name, pub, isbn, stock, alert, loc):
    try:
        # ID自動生成
        max_id = df_items['商品ID'].max()
        new_id = int(max_id) + 1 if pd.notna(max_id) else 1
        
        final_isbn = isbn if isbn else f"TEMP-{int(datetime.now().timestamp())}"
        
        # 商品マスタ追加
        ws_items.append_row([new_id, name, final_isbn, pub, stock, alert, loc])
        # ログ追加
        add_log(ws_logs, "新規登録", new_id, name, stock)
        
        st.success(f"「{name}」を登録しました")
        st.rerun()
    except Exception as e:
        st.error(f"登録エラー: {e}")

def add_log(ws_logs, action, item_id, item_name, change):
    # 連番ID生成（最新+1）
    try:
        latest = ws_logs.cell(2, 1).value
        new_log_id = int(latest) + 1 if latest and latest.isdigit() else 1
    except:
        new_log_id = 1
        
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    # 2行目に挿入（常に一番上）
    ws_logs.insert_row([new_log_id, now, action, item_id, change, item_name], index=2)

if __name__ == "__main__":
    main()