def convert_nomadnet_string_data_to_map(path_data: str | None):
    data = {}
    if path_data is not None:
        for field in path_data.split("|"):
            if "=" in field:
                parts = field.split("=", 1)
                if len(parts) == 2:
                    variable_name, variable_value = parts
                    data[f"var_{variable_name}"] = variable_value
            else:
                print(f"unhandled field: {field}")
    return data


def convert_nomadnet_field_data_to_map(field_data):
    if field_data is None:
        return None
    data = {}
    try:
        if isinstance(field_data, dict):
            data = {f"field_{key}": value for key, value in field_data.items()}
        else:
            return None
    except Exception as e:
        print(f"skipping invalid field data: {e}")
        return None
    return data


class NomadNetworkManager:
    def __init__(self, config, archiver_manager, database):
        self.config = config
        self.archiver_manager = archiver_manager
        self.database = database

    def archive_page(
        self,
        destination_hash: str,
        page_path: str,
        content: str,
        is_manual: bool = False,
    ):
        if not is_manual and not self.config.page_archiver_enabled.get():
            return

        self.archiver_manager.archive_page(
            destination_hash,
            page_path,
            content,
            max_versions=self.config.page_archiver_max_versions.get(),
            max_storage_gb=self.config.archives_max_storage_gb.get(),
        )

    def get_archived_page_versions(self, destination_hash: str, page_path: str):
        return self.database.misc.get_archived_page_versions(
            destination_hash,
            page_path,
        )

    def flush_all_archived_pages(self):
        self.database.misc.delete_archived_pages()
