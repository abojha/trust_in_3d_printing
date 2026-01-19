# trust_layer/reference_loader.py

import json


class TrustReference:
    """
    Loads layer-wise trust reference generated from Cura G-code.
    """
    def __init__(self, reference_path):
        with open(reference_path, "r") as f:
            self.layers = json.load(f)

        # Index by layer_index
        self.layer_map = {
            layer["layer_index"]: layer for layer in self.layers
        }

    def get_layer(self, layer_index):
        return self.layer_map.get(layer_index)
