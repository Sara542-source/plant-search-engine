import os
import json

def charger_stock_scientifique(filepath: str) -> set:
    stock = set()
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                stock.update({item.lower().strip() for item in data})
            elif isinstance(data, dict):
                stock.update({key.lower().strip() for key in data.keys()})
    return stock