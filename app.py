import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# ---------------------------------------------------------
# 設定・接続部分
# ---------------------------------------------------------

st.set_page_config(page_title="教科書在庫管理", layout="wide")

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
        # データが空の場合の対策
        if not items_data:
            return None, None, pd.DataFrame(), None, pd.DataFrame()
            
        df_items = pd.DataFrame(items_data[1:], columns=items_data[0])
        
        ws_logs = sh.worksheet('入出庫履歴')
        logs_data = ws_logs.get_all_values()
        df_logs = pd.DataFrame(logs_data[1:], columns=logs_data[0]) if logs_data else pd.DataFrame()
        
        return sh, ws_items, df_items, ws_logs, df_logs
    except Exception as e:
        st.error(f"スプレッドシートへの接続エラー: {e}")
        return None, None, None, None, None

# ---------------------------------------------------------
# メイン画面処理
# ---------------------------------------------------------

def main():
    st.title("📚 教科書在庫管理システム")

    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None:
        return

    # ★ここが修正ポイント：列名の「見えない空白」を自動削除！
    df_items.columns = df_items.columns.str.strip()

    try:
        df_items['商品ID'] = pd.to_numeric(df_items['商品ID'])
        df_items['現在在庫数'] = pd.to_numeric(df_items['現在在庫数'])
        df_items['発注点'] = pd.to_numeric(df_items['発注点'])
    except:
        st.warning("データの数値変換に失敗しました。")

    df_items = df_items.sort_values('商品ID', ascending=False)

    tab1, tab2, tab3 = st.tabs(["📋 在庫一覧・操作", "➕ 新規登録", "📜 履歴ログ"])

    with tab1:
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input("🔍 検索", placeholder="キーワード...")
        with col2:
            if st.button("🔄 更新"):
                st.rerun()

        if search_query:
            mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
            df_display = df_items[mask]
        else:
            df_display = df_items

        with st.expander("📦 入庫・出庫の操作", expanded=True):
            options = {f"{row['商品ID']}: {row['教科書名']}": row['商品ID'] for index, row in df_items.iterrows()}
            selected_label = st.selectbox("教科書を選択", options=list(options.keys()))
            
            if selected_label:
                selected_id = options[selected_label]
                current_item = df_items[df_items['商品ID'] == selected_id].iloc[0]
                
                c1, c2, c3 = st.columns(3)
                c1.metric("在庫", f"{current_item['現在在庫数']} 冊")
                action_type = c2.radio("操作", ["入庫", "出庫"], horizontal=True)
                quantity = c3.number_input("数量", min_value=1, value=10)

                if st.button("実行"):
                    update_stock(ws_items, ws_logs, selected_id, current_item['教科書名'], current_item['現在在庫数'], quantity, action_type)

        st.subheader("在庫リスト")
        
        # エラーが出たら原因を教える機能
        display_cols = ['教科書名', '出版社', '現在在庫数', '保管場所', 'ISBNコード']
        
        # 必要な列があるかチェック
        missing_cols = [col for col in display_cols if col not in df_items.columns]
        if missing_cols:
            st.error(f"⚠️ エラー：以下の列名がシートに見つかりません！")
            st.code(f"見つからない列: {missing_cols}")
            st.info("👇 **実際のシートの列名はこうなっています（確認してください）**")
            st.write(df_items.columns.tolist())
        else:
            def highlight_low_stock(row):
                if row['現在在庫数'] <= row['発注点']:
                    return ['background-color: #ffe6e6; color: #cc0000'] * len(row)
                return [''] * len(row)

            st.dataframe(
                df_display[display_cols].style.apply(highlight_low_stock, axis=1),
                use_container_width=True,
                height=400
            )

    with tab2:
        st.subheader("新規登録")
        with st.form("add"):
            name = st.text_input("教科書名 *")
            pub = st.text_input("出版社 *") # 簡易化
            isbn = st.text_input("ISBN")
            c1, c2, c3 = st.columns(3)
            stock = c1.number_input("初期在庫 *", 0)
            alert = c2.number_input("発注点", 10)
            loc = c3.text_input("場所")
            if st.form_submit_button("登録"):
                if not name: st.error("教科書名は必須")
                else:
                    new_id = int(df_items['商品ID'].max()) + 1
                    ws_items.append_row([new_id, name, isbn, pub, stock, alert, loc])
                    add_log(ws_logs, "新規登録", new_id, name, stock)
                    st.success("登録しました")
                    st.rerun()

    with tab3:
        st.subheader("履歴")
        st.dataframe(df_logs, use_container_width=True)

def update_stock(ws_items, ws_logs, item_id, item_name, current_stock, quantity, action_type):
    new_stock = current_stock + quantity if action_type == "入庫" else current_stock - quantity
    cell = ws_items.find(str(item_id), in_column=1)
    ws_items.update_cell(cell.row, 5, new_stock)
    add_log(ws_logs, action_type, item_id, item_name, quantity if action_type == "入庫" else -quantity)
    st.success("完了")
    st.rerun()

def add_log(ws_logs, action_type, item_id, item_name, change_val):
    try:
        latest = ws_logs.cell(2, 1).value
        new_id = int(latest) + 1 if latest and latest.isdigit() else 1
    except: new_id = 1
    ws_logs.insert_row([new_id, datetime.now().strftime("%Y/%m/%d %H:%M"), action_type, item_id, change_val, item_name], 2)

if __name__ == "__main__":
    main()
