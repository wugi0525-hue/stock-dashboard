import streamlit as st
import pandas as pd
import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="오산 조종석: 주식 분석 대시보드", layout="wide")
st.title("📊 종목별 PER vs 섹터 평균 비교 분석 (v1.1)") # <-- 버전을 표시하여 변경 확인
st.write("S&P 500 종목의 주가 추이와 섹터 평균 대비 밸류에이션을 분석합니다.")

# 2. 구글 시트 연결 설정 (로컬/클라우드 환경 구분)
@st.cache_resource
def get_gspread_client():
    # Streamlit Cloud 환경인지 확인
    if "google_key" in st.secrets and st.secrets["google_key"]:
        credentials_info = json.loads(st.secrets["google_key"])
        gc = gspread.service_account_from_dict(credentials_info)
    # 로컬 환경
    else:
        gc = gspread.service_account(filename='stock-key.json')
    return gc

# 3. 데이터 불러오기 함수 (캐싱 적용)
@st.cache_data
def load_all_data():
    client = get_gspread_client()
    spreadsheet = client.open("Stock Data")
    
    # 각 시트 읽어오기
    usa_df = pd.DataFrame(spreadsheet.worksheet("USA_Stocks").get_all_records())
    sector_df = pd.DataFrame(spreadsheet.worksheet("Sector_Trend").get_all_records())
    
    # 날짜 형식 변환 (비교를 위해 필수, 시간 제거)
    usa_df['Date'] = pd.to_datetime(usa_df['Date']).dt.normalize()
    sector_df['Date'] = pd.to_datetime(sector_df['Date']).dt.normalize()
    
    # 표시용 이름(Display_Name) 생성 함수
    def create_display_name(df):
        if 'Name' in df.columns and 'Ticker' in df.columns:
            df['Display_Name'] = df['Name'] + " (Ticker: " + df['Ticker'] + ")"
        elif 'Ticker' in df.columns:
            df['Display_Name'] = df['Ticker']
        return df

    usa_df = create_display_name(usa_df)
    
    return usa_df, sector_df

# 데이터 로드 및 인터랙티브 UI
try:
    df_usa, df_sector = load_all_data()

    st.sidebar.header("🔍 분석 설정")

    # 국가 선택: USA 또는 KOR
    country = st.sidebar.selectbox("국가 선택", ['USA', 'KOR'])

    # 선택한 국가에 따라 데이터 선택
    if country == 'USA':
        stock_sheet_df = df_usa
    else:
        # KOR 시트는 구글 시트에 KOR_Stocks로 업로드되어 있어야 함
        # 현재 load_all_data()는 USA와 Sector만 불러오므로 KOR 시트 직접 읽기
        client = get_gspread_client()
        spreadsheet = client.open("Stock Data")
        kor_df = pd.DataFrame(spreadsheet.worksheet("KOR_Stocks").get_all_records())
        kor_df['Date'] = pd.to_datetime(kor_df['Date'])
        # 표시용 이름 생성
        if 'Name' in kor_df.columns and 'Ticker' in kor_df.columns:
            kor_df['Display_Name'] = kor_df['Name'] + " (Ticker: " + kor_df['Ticker'] + ")"
        elif 'Ticker' in kor_df.columns:
            kor_df['Display_Name'] = kor_df['Ticker']
        stock_sheet_df = kor_df

    # 종목 선택 (선택박스 또는 멀티셀렉트)
    # Display_Name 기준으로 정렬 및 선택
    all_display_names = sorted(stock_sheet_df['Display_Name'].unique())

    # 기간 선택 (date range)
    min_date = stock_sheet_df['Date'].min().date()
    max_date = stock_sheet_df['Date'].max().date()
    start_date, end_date = st.sidebar.date_input("기간 선택", [min_date, max_date], min_value=min_date, max_value=max_date)

    # --- 네비게이션 처리 (표 클릭 시 이동) ---
    if 'nav_target' in st.session_state:
        target = st.session_state['nav_target']
        # 메인 메뉴 강제 변경
        st.session_state['main_menu_key'] = target['menu']
        # 티커 정보 잠시 저장 (아래 selectbox 처리에서 사용)
        st.session_state['pending_ticker'] = target['ticker']
        # 처리 완료 후 타겟 삭제
        del st.session_state['nav_target']

    # 메뉴: 상세분석 vs 랭킹
    menu = st.sidebar.radio("메뉴 선택", ['종목 상세분석', 'EPS 괴리율 랭킹'], key='main_menu_key')

    if menu == '종목 상세분석':
        # 랭킹 표에서 넘어온 티커가 있다면, Display Name을 찾아 selectbox 값을 강제 설정
        if 'pending_ticker' in st.session_state:
            target_ticker = st.session_state['pending_ticker']
            for name in all_display_names:
                if f"(Ticker: {target_ticker})" in name or name == target_ticker:
                    st.session_state['stock_selector_key'] = name
                    break
            del st.session_state['pending_ticker']

        selected_display = st.sidebar.selectbox("종목을 선택하세요", all_display_names, key='stock_selector_key')
        # 선택된 Display Name에서 Ticker 찾기
        selected_ticker = stock_sheet_df[stock_sheet_df['Display_Name'] == selected_display]['Ticker'].iloc[0]
        
        # 선택 종목 데이터 필터링
        target_stock_df = stock_sheet_df[stock_sheet_df['Ticker'] == selected_ticker].copy()
        target_stock_df = target_stock_df[(target_stock_df['Date'].dt.date >= start_date) & (target_stock_df['Date'].dt.date <= end_date)].sort_values('Date')

        if target_stock_df.empty:
            st.warning("선택 기간/종목에 대한 데이터가 없습니다.")
        else:
            # 섹터 정보
            current_sector = target_stock_df['Sector'].iloc[0] if 'Sector' in target_stock_df.columns else None
            if current_sector:
                st.sidebar.info(f"선택 종목 섹터: {current_sector}")
                target_sector_df = df_sector[df_sector['Sector'] == current_sector].copy()
                target_sector_df = target_sector_df[(target_sector_df['Date'].dt.date >= start_date) & (target_sector_df['Date'].dt.date <= end_date)].sort_values('Date')
            else:
                target_sector_df = pd.DataFrame()

            # PER 컬럼 이름 정리: 기업 PER과 섹터 PER 후보
            company_per_col = None
            for c in ['Implied PER', 'NTM_PER', 'PER', 'Implied_PER']:
                if c in target_stock_df.columns:
                    company_per_col = c
                    break

            sector_per_col = None
            for c in ['Sector PER', 'Avg PER', 'Sector_PER', 'Avg_PER']:
                if c in df_sector.columns:
                    sector_per_col = c
                    break

            # 병합: 회사 데이터와 섹터 PER (날짜 기준 left join)
            merged_df = target_stock_df.copy()
            if not target_sector_df.empty and sector_per_col:
                merged_df = pd.merge(merged_df, target_sector_df[['Date', sector_per_col]], on='Date', how='left')
                merged_df = merged_df.rename(columns={sector_per_col: 'Sector_PER'})
            else:
                merged_df['Sector_PER'] = None

            # 숫자 변환
            if company_per_col:
                merged_df[company_per_col] = pd.to_numeric(merged_df[company_per_col], errors='coerce')
            merged_df['Sector_PER'] = pd.to_numeric(merged_df['Sector_PER'], errors='coerce')

            # PER band 계산 (mean +/- std) — 데이터 기간 기준
            per_mean = merged_df[company_per_col].mean() if company_per_col else None
            per_std = merged_df[company_per_col].std() if company_per_col else None
            comp_low = per_mean - per_std if per_mean is not None and per_std is not None else None
            comp_high = per_mean + per_std if per_mean is not None and per_std is not None else None

            sec_mean = merged_df['Sector_PER'].mean() if 'Sector_PER' in merged_df and not merged_df['Sector_PER'].isna().all() else None
            sec_std = merged_df['Sector_PER'].std() if 'Sector_PER' in merged_df and not merged_df['Sector_PER'].isna().all() else None
            sec_low = sec_mean - sec_std if sec_mean is not None and sec_std is not None else None
            sec_high = sec_mean + sec_std if sec_mean is not None and sec_std is not None else None

            # 6. 주가 중심 그래프 (오른쪽 PER 축 제거)
            price_col = 'Price' if 'Price' in merged_df.columns else ('Close' if 'Close' in merged_df.columns else None)

        # EPS 찾기: 우선 NTM_EPS 등 후보 컬럼 사용, 없으면 price / PER로 역산
        eps_col = None
        for c in ['NTM_EPS', 'Implied EPS', 'Implied_EPS', 'EPS', 'Est_EPS']:
            if c in merged_df.columns:
                eps_col = c
                break

        if eps_col:
            eps_series = pd.to_numeric(merged_df[eps_col], errors='coerce')
        else:
            if company_per_col and price_col:
                eps_series = merged_df[price_col] / merged_df[company_per_col].replace({0: pd.NA})
            else:
                eps_series = pd.Series([pd.NA]*len(merged_df), index=merged_df.index)

        # 그래프 그리기 전 데이터 수집용 리스트 초기화
        show_sector_line = st.checkbox("섹터 평균 PER 기준가 표시", value=False)
        y_values = []
        fig = go.Figure()

        # 1. 주가 라인 (가장 중요하므로 진하고 두껍게)
        if price_col:
            fig.add_trace(go.Scatter(x=merged_df['Date'], y=merged_df[price_col], name='현재 주가', line=dict(color='royalblue', width=3), zorder=10))
            y_values.append(merged_df[price_col])

        # 2. PER 밴드 라인 (최저/최고 PER 2줄만 표시)
        valid_per = merged_df[company_per_col].dropna() if company_per_col else pd.Series()
        
        if not valid_per.empty and not eps_series.isna().all():
            p_min = valid_per.min()
            p_max = valid_per.max()
            
            # 최저, 최고 PER 설정
            multipliers = [p_min, p_max]
            band_labels = [f"최저 PER({p_min:.1f}배)", f"최고 PER({p_max:.1f}배)"]
            band_colors = ['#2ca02c', '#d62728'] # 초록(저평가 영역), 빨강(고평가 영역)
            
            for i, mult in enumerate(multipliers):
                if pd.isna(mult): continue
                # PER 배수 * EPS = 밴드 가격
                band_line = eps_series * mult
                color = band_colors[i]
                label = band_labels[i]
                
                fig.add_trace(go.Scatter(
                    x=merged_df['Date'], 
                    y=band_line, 
                    name=label,
                    line=dict(color=color, width=1.2, dash='dot'),
                    hoverinfo='y+name'
                ))
                y_values.append(band_line)

        # 3. 섹터 평균 PER 선
        # 의미: 이 종목이 섹터 평균만큼의 평가(PER)를 받는다면 주가가 얼마여야 하는가? (EPS * Sector PER)
        if show_sector_line and 'Sector_PER' in merged_df and not merged_df['Sector_PER'].isna().all():
            sec_line = eps_series * merged_df['Sector_PER']
            fig.add_trace(go.Scatter(
                x=merged_df['Date'], 
                y=sec_line, 
                name='섹터 평균 PER 기준가', 
                line=dict(color='gray', width=1.2, dash='dot'),
                opacity=0.7,
                hovertemplate='섹터평균기준: %{y:.1f}'
            ))
            y_values.append(sec_line)
            
        # Y축 범위 계산
        y_min, y_max = 0, 1
        if y_values:
            all_y = pd.concat(y_values).dropna()
            if not all_y.empty:
                y_min = all_y.min()
                y_max = all_y.max()
        
        y_range = y_max - y_min
        if y_range == 0:
            y_range = abs(y_max) * 0.1 if y_max != 0 else 1.0
        
        y_margin = y_range * 0.2  # 여유 20%

        fig.update_layout(
            title_text=f"<b>{selected_display}</b> 밴드 차트<br><sup>(PER 밴드 vs 주가)</sup>",
            hovermode='x unified',
            legend=dict(orientation='h', yanchor='top', y=0.99, xanchor='left', x=0.01)
        )

        # x축 날짜 포맷
        fig.update_xaxes(tickformat="%Y-%m-%d")
        fig.update_yaxes(title_text='<b>주가</b>', range=[y_min - y_margin, y_max + y_margin], tickformat=".1f", hoverformat=".1f")

        st.plotly_chart(fig, use_container_width=True)

        # 기초 통계 (소수점 1자리)
        last_price = merged_df[price_col].iloc[-1] if price_col in merged_df and not merged_df[price_col].isna().all() else None
        first_price = merged_df[price_col].iloc[0] if price_col in merged_df and not merged_df[price_col].isna().all() else None
        price_ret = (last_price - first_price) / first_price * 100 if first_price and last_price else None
        
        last_eps = eps_series.iloc[-1] if not eps_series.isna().all() else None
        first_eps = eps_series.iloc[0] if not eps_series.isna().all() else None
        eps_ret = (last_eps - first_eps) / abs(first_eps) * 100 if first_eps and last_eps and first_eps!=0 else None
        
        st.subheader("📊 기초 통계")
        col1, col2, col3 = st.columns(3)
        col1.metric("주가 변동률", f"{price_ret:.1f}%" if price_ret is not None else "-")
        col2.metric("EPS 변동률", f"{eps_ret:.1f}%" if eps_ret is not None else "-")

        # Analyst Count 표시
        last_analyst_count = merged_df['Analyst_Count'].iloc[-1] if 'Analyst_Count' in merged_df.columns and not merged_df['Analyst_Count'].isna().all() else None
        col3.metric("애널리스트 수", f"{int(last_analyst_count)}명" if last_analyst_count is not None else "-")

        # --- EPS vs 주가 비교(오른쪽 y축) 추가 그래프 ---
        eps_plot = eps_series.copy()
        eps_plot = pd.to_numeric(eps_plot, errors='coerce')
        
        # 주가 y축 범위 계산 (위아래 여유 50%)
        y1_min, y1_max = 0, 1
        if price_col and not merged_df.empty:
            y1_min = merged_df[price_col].min()
            y1_max = merged_df[price_col].max()
            
            y1_range = y1_max - y1_min
            if y1_range == 0:
                y1_range = abs(y1_max) * 0.1 if y1_max != 0 else 1.0
            y1_margin = y1_range * 0.5
            
            # EPS y축 범위 계산 (위아래 여유 50%)
            eps_valid = eps_plot.dropna()
            if not eps_valid.empty:
                y2_min = eps_valid.min()
                y2_max = eps_valid.max()
                y2_range = y2_max - y2_min
                if y2_range == 0:
                    y2_range = abs(y2_max) * 0.1 if y2_max != 0 else 1.0
                y2_margin = y2_range * 0.5
            else:
                y2_min, y2_max, y2_margin = 0, 1, 0.5

            fig2 = go.Figure()
            if price_col:
                fig2.add_trace(go.Scatter(x=merged_df['Date'], y=merged_df[price_col], name='주가', line=dict(color='royalblue', width=2), yaxis='y1'))
            fig2.add_trace(go.Scatter(x=merged_df['Date'], y=eps_plot, name='EPS', line=dict(color='orange', width=2, dash='dot'), yaxis='y2'))
            
            fig2.update_layout(
                title_text=f"{selected_display} 주가(왼쪽) vs EPS(오른쪽) 비교",
                xaxis=dict(tickformat="%Y-%m-%d"),
                yaxis=dict(
                    title=dict(text='주가', font=dict(color='royalblue')),
                    tickfont=dict(color='royalblue'),
                    range=[y1_min - y1_margin, y1_max + y1_margin],
                    tickformat=".1f", hoverformat=".1f"
                ),
                yaxis2=dict(
                    title=dict(text='EPS', font=dict(color='orange')),
                    tickfont=dict(color='orange'),
                    overlaying='y', 
                    side='right', 
                    showgrid=False,
                    range=[y2_min - y2_margin, y2_max + y2_margin],
                    tickformat=".1f", hoverformat=".1f"
                ),
                legend=dict(orientation='h', yanchor='top', y=0.99, xanchor='left', x=0.01),
                hovermode='x unified'
            )
            
            st.plotly_chart(fig2, use_container_width=True)
            # 상세 표 (날짜를 YYYY-MM-DD로 표시)
            st.subheader("📋 데이터 상세 보기")
            
            # EPS 추가
            merged_df['EPS'] = eps_series
            
            base_cols = ['Date', 'Name', 'Ticker'] if 'Name' in merged_df.columns else ['Date', 'Ticker']
            show_cols_candidate = base_cols + [price_col, 'EPS', company_per_col, 'Sector_PER', 'Analyst_Count']
            show_cols = [col for col in show_cols_candidate if col and col in merged_df.columns]
            
            display_df = merged_df[show_cols].copy()

            # PER 수치 소수점 1자리 반올림
            if company_per_col and company_per_col in display_df.columns:
                display_df[company_per_col] = display_df[company_per_col].round(1)
            if 'Sector_PER' in display_df.columns:
                display_df['Sector_PER'] = display_df['Sector_PER'].round(1)
            if 'EPS' in display_df.columns:
                display_df['EPS'] = pd.to_numeric(display_df['EPS'], errors='coerce').round(2)
            if 'Analyst_Count' in display_df.columns:
                display_df['Analyst_Count'] = pd.to_numeric(display_df['Analyst_Count'], errors='coerce').astype('Int64') # NaN 처리 위해 Int64
            if 'Date' in display_df.columns:
                display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
            st.dataframe(display_df.sort_values('Date', ascending=False), hide_index=True)

    else:
        # EPS 괴리율 랭킹
        st.header('📈 EPS 괴리율 랭킹')
        st.write(f'기간: {start_date} ~ {end_date} | 국가: {country}')

        tickers_list = sorted(stock_sheet_df['Ticker'].unique())
        rows = []
        for tk in tickers_list:
            df_t = stock_sheet_df[stock_sheet_df['Ticker'] == tk].copy()
            df_t = df_t[(df_t['Date'].dt.date >= start_date) & (df_t['Date'].dt.date <= end_date)].sort_values('Date')
            if df_t.empty:
                continue
            price_col_local = 'Price' if 'Price' in df_t.columns else ('Close' if 'Close' in df_t.columns else None)
            if not price_col_local:
                continue
            p0 = pd.to_numeric(df_t[price_col_local], errors='coerce').iloc[0]
            p1 = pd.to_numeric(df_t[price_col_local], errors='coerce').iloc[-1]
            if pd.isna(p0) or pd.isna(p1) or p0==0:
                continue
            price_change = (p1 - p0) / p0 * 100

            # eps change
            eps_col_local = None
            for c in ['NTM_EPS', 'Implied EPS', 'Implied_EPS', 'EPS', 'Est_EPS']:
                if c in df_t.columns:
                    eps_col_local = c
                    break
            if eps_col_local:
                e0 = pd.to_numeric(df_t[eps_col_local], errors='coerce').iloc[0]
                e1 = pd.to_numeric(df_t[eps_col_local], errors='coerce').iloc[-1]
                if pd.isna(e0) or pd.isna(e1) or e0==0:
                    continue
                eps_change = (e1 - e0) / abs(e0) * 100
            else:
                # try via PER
                per_col_local = None
                for c in ['Implied PER', 'NTM_PER', 'PER', 'Implied_PER']:
                    if c in df_t.columns:
                        per_col_local = c
                        break
                if per_col_local and per_col_local in df_t.columns:
                    per0 = pd.to_numeric(df_t[per_col_local], errors='coerce').iloc[0]
                    per1 = pd.to_numeric(df_t[per_col_local], errors='coerce').iloc[-1]
                    if pd.isna(per0) or pd.isna(per1) or per0==0:
                        continue
                    e0 = p0 / per0
                    e1 = p1 / per1
                    if e0==0:
                        continue
                    eps_change = (e1 - e0) / abs(e0) * 100
                else:
                    continue

            divergence = abs(price_change - eps_change)
            sector_val = df_t['Sector'].iloc[0] if 'Sector' in df_t.columns else ''
            name_val = df_t['Name'].iloc[0] if 'Name' in df_t.columns else ''
            rows.append({'Name': name_val, 'Ticker': tk, 'Sector': sector_val, 'Price Change (%)': price_change, 'EPS Change (%)': eps_change, 'Divergence': divergence})

        if not rows:
            st.info('해당 기간 내 데이터가 부족하여 랭킹을 생성할 수 없습니다.')
        else:
            # 컬럼 순서 지정: Name, Ticker, Sector 순
            cols_order = ['Name', 'Ticker', 'Sector', 'Price Change (%)', 'EPS Change (%)', 'Divergence']
            df_rank = pd.DataFrame(rows)[cols_order].sort_values('Divergence', ascending=False).reset_index(drop=True)
            # 인덱스를 1부터 시작하도록 조정
            df_rank.index = df_rank.index + 1
            
            # 소수점 1자리로 반올림
            cols_to_round = ['Price Change (%)', 'EPS Change (%)', 'Divergence']
            df_rank[cols_to_round] = df_rank[cols_to_round].round(1)

            top_n = st.sidebar.number_input('상위 N개 표시', min_value=5, max_value=200, value=50)
            
            st.write("💡 표에서 행을 선택하면 해당 종목의 상세 분석 화면으로 이동합니다.")
            event = st.dataframe(
                df_rank.head(top_n),
                on_select='rerun',
                selection_mode='single-row'
            )
            
            if len(event.selection['rows']) > 0:
                selected_row_index = event.selection['rows'][0]
                selected_ticker_from_table = df_rank.iloc[selected_row_index]['Ticker']
                # 세션 상태 업데이트 및 이동
                st.session_state['nav_target'] = {'menu': '종목 상세분석', 'ticker': selected_ticker_from_table}
                st.rerun()

            import plotly.express as px

            # Y축 범위 조정
            max_divergence = df_rank['Divergence'].head(top_n).max()
            y_max_limit = max_divergence * 1.1 # 최대값보다 조금 더 크게 설정
            
            # 특정 값 이상이면 Y축 끊기 (예: 50% 이상 차이나는 경우)
            # plotly bar chart는 yaxis range breaks를 직접 지원하지 않으므로
            # 데이터를 필터링하거나, 또는 Y축 최대값을 설정하는 방식으로 조정합니다.
            # 여기서는 Y축 최대값을 설정하여 너무 큰 값들이 그래프 전체를 지배하지 않도록 합니다.
            
            # 만약 아주 극단적인 값이 있다면, 특정 임계값으로 잘라내는 옵션을 추가할 수 있습니다.
            # 예를 들어, divergence가 1000% 이상인 경우 1000%로 제한
            # df_rank['Divergence'] = df_rank['Divergence'].clip(upper=1000) # 예시
            
            fig_rank = px.bar(
                df_rank.head(top_n),
                x='Ticker',
                y='Divergence',
                color='Sector',
                hover_name='Name',
                hover_data={'Ticker':True, 'Sector':True, 'Price Change (%)':True, 'EPS Change (%)':True, 'Divergence':True},
                title="종목별 가격-이익 괴리율 (Divergence)"
            )
            
            # 격차가 너무 클 경우를 대비해 로그 스케일 선택 옵션 제공
            use_log = st.checkbox("로그 스케일 사용 (격차가 큰 경우 유용)", value=False)
            if use_log:
                fig_rank.update_layout(yaxis_type="log")
                st.info("💡 로그 스케일이 적용되었습니다. 값이 작은 종목들도 더 잘 보입니다.")
            else:
                # 일반 스케일일 때 너무 큰 값 때문에 다른게 안보이는걸 방지하기 위해 상한선 조정 (선택 사항)
                pass

            st.plotly_chart(fig_rank, use_container_width=True)


except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.info("구글 시트의 탭 이름(USA_Stocks, KOR_Stocks, Sector_Trend)과 컬럼명(Ticker, Date, Sector, Price/Close, Implied PER 또는 NTM_PER, Sector PER 또는 Avg PER)이 일치하는지 확인해 주세요.")