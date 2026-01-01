from .announces import AnnounceDAO
from .config import ConfigDAO
from .legacy_migrator import LegacyMigrator
from .messages import MessageDAO
from .misc import MiscDAO
from .provider import DatabaseProvider
from .schema import DatabaseSchema
from .telephone import TelephoneDAO


class Database:
    def __init__(self, db_path):
        self.provider = DatabaseProvider.get_instance(db_path)
        self.schema = DatabaseSchema(self.provider)
        self.config = ConfigDAO(self.provider)
        self.messages = MessageDAO(self.provider)
        self.announces = AnnounceDAO(self.provider)
        self.misc = MiscDAO(self.provider)
        self.telephone = TelephoneDAO(self.provider)

    def initialize(self):
        self.schema.initialize()

    def migrate_from_legacy(self, reticulum_config_dir, identity_hash_hex):
        migrator = LegacyMigrator(self.provider, reticulum_config_dir, identity_hash_hex)
        if migrator.should_migrate():
            return migrator.migrate()
        return False

    def execute_sql(self, query, params=None):
        return self.provider.execute(query, params)

    def close(self):
        self.provider.close()

