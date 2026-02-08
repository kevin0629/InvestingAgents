from src.get_data import Data


_data_instance = None
def get_data_instance():
    global _data_instance
    if _data_instance is None:
        print("Loading Data Instance for the first time...")
        _data_instance = Data(use_cache=True)
    return _data_instance