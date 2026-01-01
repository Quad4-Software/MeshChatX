class InterfaceEditor:
    @staticmethod
    def update_value(interface_details: dict, data: dict, key: str):
        # update value if provided and not empty
        value = data.get(key)
        if value is not None and value != "":
            interface_details[key] = value
            return

        # otherwise remove existing value
        interface_details.pop(key, None)
