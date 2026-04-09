from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from src.stock.schemas import StockChartQueryParams
from src.stock.service import StockService
from typing import Optional
from src.utils import get_data_instance

router = APIRouter(prefix="/stock", tags=["stock"])


@router.get("/taiex/chart", responses={200: {"content": {"image/png": {}}}})
async def get_taiex_chart(
    params: StockChartQueryParams = Depends()
):
    """
    獲取台灣加權指數 K 線圖 (包含成交量與移動平均線)
    """
    try:
        data = get_data_instance()
        service = StockService(data, "TAIEX", params.end_date)
        image_buf = service.get_taiex_chart(params)
        return StreamingResponse(image_buf, media_type="image/png")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

@router.get("/{company_symbol}/chart", responses={200: {"content": {"image/png": {}}}})
async def get_stock_chart(
    company_symbol: str,
    params: StockChartQueryParams = Depends()
):
    """
    獲取股票 K 線圖 (包含成交量與移動平均線)
    """
    try:
        data = get_data_instance()
        service = StockService(data, company_symbol)
        image_buf = service.get_stock_chart(params)
        return StreamingResponse(image_buf, media_type="image/png")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@router.get("/{company_symbol}/river", responses={200: {"content": {"image/png": {}}}})
async def get_river_chart(
    company_symbol: str,
    end_date: Optional[str] = None,
):
    """
    獲取股票本益比河流圖
    """
    try:
        data = get_data_instance()
        service = StockService(data, company_symbol, end_date)
        image_buf = service.get_stock_river_chart()
        return StreamingResponse(image_buf, media_type="image/png")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


