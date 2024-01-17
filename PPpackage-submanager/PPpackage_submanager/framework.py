from PPpackage_utils.server import Framework

from .database import Token, User

framework = Framework(Token, User)
