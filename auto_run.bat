@echo off
:: [1단계] 깨어나서 인터넷 연결될 때까지 60초만 멍하니 기다리기 (제일 중요!)
timeout /t 60 /nobreak

:: [2단계] 파이썬 파일이 있는 폴더로 이동하기
cd /d "C:\Users\wugi2"

:: [3단계] 파이썬 코드 실행하기
python stock_ntm_master.py