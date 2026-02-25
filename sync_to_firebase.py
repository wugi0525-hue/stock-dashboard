import gspread
import firebase_admin
from firebase_admin import credentials, firestore
import time
import datetime
import os
import sys

# 구글 시트 연결
def get_gspread_client():
    try:
        # 스크립트와 같은 경로에 있는 키 파일 사용
        key_path = os.path.join(os.path.dirname(__file__), 'stock-key.json')
        print(f"[Sync] 구글 시트 키로 연결 시도: {key_path}")
        gc = gspread.service_account(filename=key_path)
        return gc
    except Exception as e:
        print(f"[Error] 구글 시트 연결 실패: {e}")
        return None

# Firebase 연결
def get_firebase_client():
    try:
        if not firebase_admin._apps:
            key_path = os.path.join(os.path.dirname(__file__), 'firebase-key.json')
            print(f"[Sync] Firebase 키로 연결 시도: {key_path}")
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        print(f"[Error] Firebase 연결 실패: {e}")
        return None

def sync_collection(db, spreadsheet, sheet_name, unique_key_field):
    print(f"\n[Sync] '{sheet_name}' 동기화 시작...")
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        if not records:
            print(f"[Sync] '{sheet_name}' 에 데이터가 없습니다.")
            return

        collection_ref = db.collection(sheet_name)
        
        # Firestore batch write (최대 500개 제한 고려)
        batch = db.batch()
        count = 0
        total_synced = 0
        
        for record in records:
            # 빈 행 무시
            if not record.get('Date') and not record.get(unique_key_field):
                continue
                
            # Date 필드를 문자열로 표준화
            if 'Date' in record and record['Date']:
                record['Date'] = str(record['Date'])

            # 문서 ID 생성 (예: Ticker_Date, Sector_Date)
            # 날짜를 활용하여 고유 ID 생성 (덮어쓰기 위해)
            primary_id = str(record.get(unique_key_field, '')).strip()
            date_str = str(record.get('Date', '')).strip()
            # ID에 사용할 수 없는 특수문자 제거
            safe_primary = primary_id.replace('/', '_').replace(' ', '_')
            safe_date = date_str.replace('/', '-').replace(' ', '_')
            
            doc_id = f"{safe_primary}_{safe_date}"
            if not doc_id or doc_id == "_":
                continue # ID가 없으면 패스

            doc_ref = collection_ref.document(doc_id)
            batch.set(doc_ref, record, merge=True)
            count += 1
            
            # 배치 한도 도달 시 커밋
            if count == 450:
                batch.commit()
                total_synced += count
                print(f"       {total_synced}개 문서 커밋 완료...")
                batch = db.batch()
                count = 0
                
        if count > 0:
            batch.commit()
            total_synced += count
            
        print(f"[Sync] '{sheet_name}' 데이터 총 {total_synced}개 동기화 성공!")

    except Exception as e:
        print(f"[Error] '{sheet_name}' 동기화 중 오류: {e}")

def main():
    print(f"========== 동기화 작업 시작: {datetime.datetime.now()} ==========")
    gc = get_gspread_client()
    if not gc:
        return
        
    db = get_firebase_client()
    if not db:
        return
        
    try:
        spreadsheet = gc.open("Stock Data")
        print("[Sync] 'Stock Data' 스프레드시트 열기 성공")
        
        # 시트별 고유 키 필드 매핑하여 동기화
        sync_collection(db, spreadsheet, "USA_Stocks", "Ticker")
        sync_collection(db, spreadsheet, "Sector_Trend", "Sector")
        
        # KOR_Stocks가 있으면(옵션) 동기화
        try:
             sync_collection(db, spreadsheet, "KOR_Stocks", "Ticker")
        except:
             pass
             
    except Exception as e:
        print(f"[Error] 스프레드시트 오류: {e}")
        
    print(f"========== 동기화 작업 완료: {datetime.datetime.now()} ==========\n")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
        print("[Daemon] 구글 시트 -> 파이어베이스 자동 동기화 데몬 모드 시작 (10분 간격)")
        while True:
            main()
            time.sleep(600) # 10분(600초)마다 반복
    else:
        main()
