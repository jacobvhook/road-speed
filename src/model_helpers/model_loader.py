from model_helpers.model_paths import MODEL_PATHS
import pickle


class ModelLoader:
    def __init__(self):
        pass

    def load(self, model_type: str):
        model_path = MODEL_PATHS[model_type]
        with open(model_path, "rb") as f:
            return pickle.load(f)
