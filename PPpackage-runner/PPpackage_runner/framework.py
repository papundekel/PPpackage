from PPpackage_runner.database import TokenDB, User
from PPpackage_utils.server import Framework

framework = Framework(TokenDB, User)
