class StorageBackend:
    def list_objects(self, prefix: str):
        raise NotImplementedError
    
    def get_object(self, key: str) -> bytes:
        raise NotImplementedError

    def load_day(storage: StorageBackend, day: str):
        prefix = f"{day}/embeds/"
        
        for obj in storage.list_objects(prefix):
            data = storage.get_object(obj.object_name)
            # parse embedding, json, whatever