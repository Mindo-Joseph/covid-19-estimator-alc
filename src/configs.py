import os

#  Configuration classes


class Config(object):
    DEBUG = False
    TESTING = False
    DATABASE_URI = os.getenv('DB_URL')


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True
    DEVELOPMENT = True


class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    DATABASE_URI = os.getenv('TDB_URL')