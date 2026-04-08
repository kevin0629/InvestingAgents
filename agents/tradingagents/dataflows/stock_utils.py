import requests
from typing import Optional
from io import BytesIO
import matplotlib.pyplot as plt
from .utils import get_backend_base_url


def get_taiex_chart(
    end_date: Optional[str] = None,
    timeframe: str = "D"
) -> bytes:
    """
    獲取台灣加權指數 K 線圖 (包含成交量與移動平均線)
    
    Args:
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        
    Returns:
        PNG image bytes
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/stock/taiex/chart"
    
    params = {"timeframe": timeframe}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.content


def get_stock_chart(
    company_symbol: str,
    end_date: Optional[str] = None,
    timeframe: str = "D"
) -> bytes:
    """
    獲取股票 K 線圖 (包含成交量與移動平均線)
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        timeframe: 時間週期 (D=日線, W=週線, M=月線)
        
    Returns:
        PNG image bytes
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/stock/{company_symbol}/chart"
    
    params = {"timeframe": timeframe}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.content


if __name__ == "__main__":
    # Example usage
    company_symbol = "2330"
    # Get PNG bytes from backend
    # img_bytes = get_taiex_chart()
    # img_bytes = get_stock_chart(company_symbol, end_date="2024-06-30", timeframe="W")

    # Try to open with PIL if available (more robust), otherwise fall back to
    # matplotlib.image.imread which can read from a BytesIO for PNG.
    # try:
    #     from PIL import Image
    #     img = Image.open(BytesIO(img_bytes))
    #     plt.imshow(img)
    # except Exception:
    #     import matplotlib.image as mpimg
    #     img = mpimg.imread(BytesIO(img_bytes), format="png")
    #     plt.imshow(img)

    # plt.axis('off')
    # plt.show()