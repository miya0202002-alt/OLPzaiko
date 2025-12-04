import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json # ★これがクラウド対応に必須です！
from datetime import datetime

# ---------------------------------------------------------
# 設定・接続部分
# ---------------------------------------------------------

st.set_page_config(page_title="教科書在庫管理", layout="wide")

# ローカルで動かす時用のファイル名
JSON_FILE = 'secret_key.json' 
SPREADSHEET_NAME = '在庫管理システム'

@st.cache_resource
def get_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # ★ここが重要！クラウド上のSecretsがあるか確認する
    if "gcp_service_account" in st.secrets:
        # クラウド（スマホ）用：Secretsから鍵を作る
        key_dict = json.loads(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    else:
        # パソコン（ローカル）用：ファイルから鍵を作る
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        
    client = gspread.authorize(creds)
    return client

def load_data():
    client = get_connection()
    try:
        sh = client.open(SPREADSHEET_NAME)
        ws_items = sh.worksheet('商品マスタ')
        items_data = ws_items.get_all_values()
        df_items = pd.DataFrame(items_data[1:], columns=items_data[0])
        
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

    sh, ws_items, df_items, ws_logs, df_logs = load_data()
    if sh is None:
        return

    try:
        df_items['商品ID'] = pd.to_numeric(df_items['商品ID'])
        df_items['現在在庫数'] = pd.to_numeric(df_items['現在在庫数'])
        df_items['発注点'] = pd.to_numeric(df_items['発注点'])
    except:
        st.warning("データの数値変換に失敗しました。シートの形式を確認してください。")

    df_items = df_items.sort_values('商品ID', ascending=False)

    tab1, tab2, tab3 = st.tabs(["📋 在庫一覧・操作", "➕ 新規登録", "📜 履歴ログ"])

    with tab1:
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input("🔍 検索（教科書名、出版社など）", placeholder="キーワードを入力...")
        with col2:
            if st.button("🔄 更新"):
                st.rerun()

        if search_query:
            mask = df_items.apply(lambda x: search_query.lower() in str(x).lower(), axis=1)
            df_display = df_items[mask]
        else:
            df_display = df_items

        with st.expander("📦 入庫・出庫の操作はこちら", expanded=True):
            st.write("操作する教科書を選択してください")
            options = {f"{row['商品ID']}: {row['教科書名']}": row['商品ID'] for index, row in df_items.iterrows()}
            selected_label = st.selectbox("教科書を選択", options=list(options.keys()))
            
            if selected_label:
                selected_id = options[selected_label]
                current_item = df_items[df_items['商品ID'] == selected_id].iloc[0]
                
                c1, c2, c3 = st.columns(3)
                c1.metric("現在の在庫", f"{current_item['現在在庫数']} 冊")
                c1.caption(f"保管場所: {current_item['保管場所']}")
                
                action_type = c2.radio("操作", ["入庫", "出庫"], horizontal=True)
                quantity = c3.number_input("数量", min_value=1, value=1 if action_type == "出庫" else 10)

                if st.button("実行する", type="primary"):
                    update_stock(ws_items, ws_logs, selected_id, current_item['教科書名'], current_item['現在在庫数'], quantity, action_type)

        st.subheader("在庫リスト")
        def highlight_low_stock(row):
            if row['現在在庫数'] <= row['発注点']:
                return ['background-color: #ffe6e6; color: #cc0000'] * len(row)
            return [''] * len(row)

        display_cols = ['教科書名', '出版社', '現在在庫数', '保管場所', 'ISBNコード']
        st.dataframe(
            df_display[display_cols].style.apply(highlight_low_stock, axis=1),
            use_container_width=True,
            height=400
        )

    with tab2:
        st.subheader("新規教科書の登録")
        with st.form("add_item_form"):
            col_a, col_b = st.columns(2)
            new_name = col_a.text_input("教科書名 *")
            publishers = list(df_items['出版社'].unique())
            new_publisher = col_b.selectbox("出版社 *", options=publishers + ["その他（手入力）"])
            if new_publisher == "その他（手入力）":
                new_publisher = col_b.text_input("出版社名を入力")
            new_isbn = st.text_input("ISBNコード (任意)")
            c1, c2, c3 = st.columns(3)
            new_stock = c1.number_input("初期在庫数 *", min_value=0, value=0)
            new_alert = c2.number_input("発注点", min_value=0, value=10)
            new_location = c3.text_input("保管場所 (任意)")

            submit_btn = st.form_submit_button("登録する")

            if submit_btn:
                if not new_name or not new_publisher:
                    st.error("教科書名と出版社は必須です！")
                else:
                    new_id = int(df_items['商品ID'].max()) + 1
                    final_isbn = new_isbn if new_isbn else f"TEMP-{int(datetime.now().timestamp())}"
                    new_row = [new_id, new_name, final_isbn, new_publisher, new_stock, new_alert, new_location]
                    ws_items.append_row(new_row)
                    add_log(ws_logs, "新規登録", new_id, new_name, new_stock)
                    st.success(f"「{new_name}」を登録しました！")
                    st.rerun()

    with tab3:
        st.subheader("入出庫履歴（最新順）")
        try:
            df_logs['ログID'] = pd.to_numeric(df_logs['ログID'])
            df_logs = df_logs.sort_values('ログID', ascending=False)
        except:
            pass
        st.dataframe(df_logs, use_container_width=True)

def update_stock(ws_items, ws_logs, item_id, item_name, current_stock, quantity, action_type):
    try:
        new_stock = current_stock + quantity if action_type == "入庫" else current_stock - quantity
        if new_stock < 0:
            st.error("在庫不足です！")
            return
        cell = ws_items.find(str(item_id), in_column=1)
        if cell:
            ws_items.update_cell(cell.row, 5, new_stock)
            change_val = quantity if action_type == "入庫" else -quantity
            add_log(ws_logs, action_type, item_id, item_name, change_val)
            st.success(f"{action_type}完了！ 現在在庫: {new_stock}冊")
            st.rerun()
        else:
            st.error("IDが見つかりませんでした")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

def add_log(ws_logs, action_type, item_id, item_name, change_val):
    try:
        latest_id = ws_logs.cell(2, 1).value
        new_log_id = int(latest_id) + 1 if latest_id and latest_id.isdigit() else 1
    except:
        new_log_id = 1
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    new_log = [new_log_id, now, action_type, item_id, change_val, item_name]
    ws_logs.insert_row(new_log, index=2)

if __name__ == "__main__":
    main()
