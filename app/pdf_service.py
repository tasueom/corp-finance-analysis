"""
PDF 생성 서비스 모듈
PDF 차트 이미지 및 문서 생성 담당
"""
import pandas as pd
from io import BytesIO


def generate_pdf_chart_image(rows, selected_corp, selected_year):
    """PDF용 차트 이미지를 생성합니다."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager, rc
    
    important_account_ids = [
        "ifrs-full_Assets",
        "ifrs-full_CurrentAssets",
        "ifrs-full_NoncurrentAssets",
        "ifrs-full_Liabilities",
        "ifrs-full_CurrentLiabilities",
        "ifrs-full_NoncurrentLiabilities",
        "ifrs-full_Equity",
        "ifrs-full_IssuedCapital",
        "ifrs-full_RetainedEarnings",
        "ifrs-full_CashAndCashEquivalents",
        "ifrs-full_Inventories",
        "ifrs-full_PropertyPlantAndEquipment",
    ]
    
    filtered_rows = [r for r in rows if r[0] and r[0] in important_account_ids]
    
    if not filtered_rows:
        filtered_rows = rows
    
    font_path = "C:/Windows/Fonts/malgun.ttf"
    font_name = font_manager.FontProperties(fname=font_path).get_name()
    rc('font', family=font_name)
    plt.rcParams['axes.unicode_minus'] = False
    
    data = [(r[1], r[2]) for r in filtered_rows]
    df = pd.DataFrame(data, columns=["account_nm", "amount"])
    
    accounts = df["account_nm"]
    amounts = df["amount"]
    
    plt.bar(accounts, amounts)
    plt.xticks(rotation=60, ha="right")
    plt.title(f"{selected_corp} {selected_year}년 재무상태표 주요 항목", fontsize=14, pad=20)
    plt.xlabel("계정과목")
    plt.ylabel("금액(원)")
    
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight', transparent=True)
    plt.close()
    
    img_buffer.seek(0)
    return img_buffer


def generate_pdf_document(rows, selected_corp, selected_year, chart_image_buffer):
    """PDF 문서를 생성합니다."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.utils import ImageReader
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    pdfmetrics.registerFont(
        TTFont("Malgun", "C:/Windows/Fonts/malgun.ttf")
    )

    x = 50
    y = height - 50

    c.setFont("Malgun", 16)
    c.drawString(x, y, f"{selected_corp} {selected_year}년 재무상태표")
    y -= 30

    c.setFont("Malgun", 11)
    c.drawString(x, y, "계정과목")
    c.drawRightString(width - 50, y, "금액(원)")
    y -= 20

    c.setFont("Malgun", 9)

    for row in rows:
        account_nm = row[1]
        amount = row[2]
        if y < 120:
            c.showPage()
            c.setFont("Malgun", 9)
            y = height - 50

        c.drawString(x, y, str(account_nm))
        c.drawRightString(width - 50, y, f"{amount:,}")
        y -= 14
    
    chart_image_buffer.seek(0)
    c.drawImage(
        ImageReader(chart_image_buffer),
        x,
        50,
        width=500,
        height=250
    )

    c.save()
    buffer.seek(0)
    
    return buffer

