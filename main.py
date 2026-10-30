from app.database import Database
from app.ui.app import launch_app


if __name__ == "__main__":
    launch_app(Database())
