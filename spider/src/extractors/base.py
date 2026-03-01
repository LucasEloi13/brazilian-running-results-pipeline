from abc import ABC, abstractmethod
import yaml

class Extractor(ABC):
    
    def __init__(self, config: dict):
        self.config = config
        self.base_url = config["base_url"]
    
    @abstractmethod
    def extract(self, **kwargs) -> list[dict]:
        pass