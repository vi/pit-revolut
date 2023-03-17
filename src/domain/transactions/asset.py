
class AssetValue:
    def __init__(self, amount: float, asset_name: str):
        self.amount = amount
        self.asset_name = asset_name

    def __str__(self):
        return f"{self.amount} {self.asset_name}"

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
