from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from src.stock.schemas import StockChartQueryParams,StockListResponse
from src.stock.service import StockService
from src.utils import get_data_instance

router = APIRouter(prefix="/stock", tags=["stock"])

@router.get("/taiex", response_model=StockListResponse)
async def get_taiex(
    params: StockChartQueryParams = Depends()
):
    """
    獲取台灣加權指數開高低收成交量資料
    """
    try:
        service = StockService(get_data_instance())
        data = service.get_taiex_data(params)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return StockListResponse(data=data)




@router.get("/{company_symbol}", response_model=StockListResponse)
async def get_stock(
    company_symbol: str,
    params: StockChartQueryParams = Depends()
):
    """
    獲取股票開高低收成交量資料
    """
    try:
        service = StockService(get_data_instance())
        data = service.get_stock_data(company_symbol, params)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return StockListResponse(data=data)



@router.get("/taiex/chart", responses={200: {"content": {"image/png": {}}}})
async def get_taiex_chart(
    params: StockChartQueryParams = Depends()
):
    """
    獲取台灣加權指數 K 線圖 (包含成交量與移動平均線)
    """
    try:
        service = StockService(get_data_instance())
        image_buf = service.get_taiex_chart(params)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return StreamingResponse(image_buf, media_type="image/png")

    

@router.get("/{company_symbol}/chart", responses={200: {"content": {"image/png": {}}}})
async def get_stock_chart(
    company_symbol: str,
    params: StockChartQueryParams = Depends()
):
    """
    獲取股票 K 線圖 (包含成交量與移動平均線)
    """
    try:
        service = StockService(get_data_instance())
        image_buf = service.get_stock_chart(company_symbol, params)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return StreamingResponse(image_buf, media_type="image/png")


    
@router.get("/{company_symbol}/river", responses={200: {"content": {"image/png": {}}}})
async def get_river_chart(
    company_symbol: str,
    params: StockChartQueryParams = Depends()
):
    """
    獲取股票本益比河流圖
    """
    try:
        service = StockService(get_data_instance())
        image_buf = service.get_stock_river_chart(company_symbol, params)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return StreamingResponse(image_buf, media_type="image/png")