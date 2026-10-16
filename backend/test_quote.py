import asyncio
import json
from app.services.quote_service import quote_service

async def main():
    print("Testing stock and fund quote fetch...")
    items = [
        {"code": "600519", "asset_type": "stock"},  # 贵州茅台
        {"code": "161725", "asset_type": "fund"},   # 招商中证白酒指数
        {"code": "000001", "asset_type": "stock"},  # 平安银行
    ]
    quotes = await quote_service.get_multi_quotes(items)
    print("Quotes fetched successfully:")
    print(json.dumps(quotes, ensure_ascii=False, indent=2))

    search_res = await quote_service.search_symbol("招商")
    print(f"Search results for '招商': {len(search_res)} items found.")
    for it in search_res[:3]:
        print(it)

if __name__ == "__main__":
    asyncio.run(main())
